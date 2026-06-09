"""
Auto-scroll + state bridge — listens for `cascade_node_selected` events from
the DAG iframe, scrolls the page to the detail panel anchor, AND propagates
the new selection back to Streamlit via a bidirectional component.

The DAG click handler calls `window.parent.cascadePendingNodeId = uid` and
`window.parent.cascadePendingNodeAt = Date.now()`. This bridge polls every
500ms; when it sees a new value, it (a) sets Streamlit component value to
{selected_node_uid, ts} so app.py can pick it up, and (b) scrolls the page
to the detail panel.
"""

import streamlit as st
import streamlit.components.v1 as components


_BRIDGE_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  html, body { margin: 0; padding: 0; background: transparent; }
</style>
</head>
<body>
<script>
(function() {
  'use strict';
  let lastSeenAt = 0;
  let lastReportedUid = null;

  function getStreamlit() {
    try {
      if (window.Streamlit && typeof window.Streamlit.setComponentValue === 'function') return window.Streamlit;
      if (window.parent && window.parent.Streamlit && typeof window.parent.Streamlit.setComponentValue === 'function') return window.parent.Streamlit;
    } catch (e) {}
    return null;
  }

  function reportValue(uid) {
    const S = getStreamlit();
    if (S) {
      try { S.setComponentValue({selected_node_uid: uid, ts: Date.now()}); return; } catch (e) {}
    }
  }

  function getAnchor() {
    try {
      return window.parent && window.parent.document
        ? window.parent.document.getElementById('cascade-detail-panel')
        : null;
    } catch (e) { return null; }
  }

  function tryScroll() {
    const el = getAnchor();
    if (el && typeof el.scrollIntoView === 'function') {
      try { el.scrollIntoView({behavior: 'smooth', block: 'start'}); } catch (e) { try { el.scrollIntoView(); } catch (e2) {} }
    }
  }

  function poll() {
    try {
      const parent = window.parent;
      if (!parent || parent === window) return;
      const pendingUid = parent.cascadePendingNodeId;
      const pendingAt = parent.cascadePendingNodeAt || 0;
      if (pendingUid && pendingAt > lastSeenAt) {
        lastSeenAt = pendingAt;
        if (pendingUid !== lastReportedUid) {
          lastReportedUid = pendingUid;
          reportValue(pendingUid);
        }
        let attempts = 0;
        const doScroll = () => {
          attempts++;
          if (getAnchor()) tryScroll();
          else if (attempts < 10) setTimeout(doScroll, 80);
        };
        doScroll();
      }
    } catch (e) {}
  }

  setInterval(poll, 500);
  setTimeout(poll, 100);
})();
</script>
</body>
</html>
"""

# Bidirectional component: returns the latest node selection (or None).
_bridge_component = components.declare_component(
    "cascade_scroll_bridge",
    url="https://placeholder.invalid",  # not used
)


def render_scroll_bridge() -> dict | None:
    """Render the hidden bridge. Returns latest click event dict or None."""
    return _bridge_component(html=_BRIDGE_HTML, height=0, default=None)
