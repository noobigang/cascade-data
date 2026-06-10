"""
Auto-scroll + state bridge — listens for `cascade_node_selected` events from
the DAG iframe, propagates the new selection back to Streamlit via
`streamlit-js-eval`, and scrolls the page to the detail panel.

The DAG click handler sets `window.cascadePendingNodeId` and
`window.cascadePendingNodeAt = Date.now()`. This bridge polls the parent
window every 400ms; when it sees a new value, it returns it to Streamlit,
which the app reads to update `st.session_state.selected_node_uid`.
"""
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

_BRIDGE_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  html, body { margin: 0; padding: 0; background: transparent; height: 0; overflow: hidden; }
</style>
</head>
<body>
<script>
(function() {
  'use strict';
  // The DAG click handler sets these on its own window (or its parent if cross-iframed).
  // We mirror them to this window so the parent polling can see them.
  let lastSeenAt = 0;
  let lastReportedUid = null;

  function getPending() {
    try {
      // walk up: same window -> parent -> top, looking for cascadePendingNodeId
      let w = window;
      for (let i = 0; i < 5; i++) {
        if (!w) break;
        if (typeof w.cascadePendingNodeId !== 'undefined' || w.cascadePendingNodeAt) {
          return {
            uid: w.cascadePendingNodeId || null,
            at: w.cascadePendingNodeAt || 0
          };
        }
        try { w = w.parent; } catch (e) { break; }
        if (w === window) break;
      }
    } catch (e) {}
    return { uid: null, at: 0 };
  }

  window.__cascadeReport = function(uid) {
    // No-op: actual reporting is done via streamlit-js-eval polling parent.
    // This function exists for future expansion / debugging.
    console.log('[cascade-bridge] pending node:', uid);
  };

  // Auto-scroll the parent page to the detail panel on every new selection.
  function getAnchor() {
    try {
      let w = window;
      for (let i = 0; i < 5; i++) {
        if (!w) break;
        if (w.document && w.document.getElementById) {
          const el = w.document.getElementById('cascade-detail-panel');
          if (el) return el;
        }
        try { w = w.parent; } catch (e) { break; }
        if (w === window) break;
      }
    } catch (e) {}
    return null;
  }

  function tryScroll() {
    const el = getAnchor();
    if (el && typeof el.scrollIntoView === 'function') {
      try { el.scrollIntoView({behavior: 'smooth', block: 'start'}); } catch (e) { try { el.scrollIntoView(); } catch (e2) {} }
    }
  }

  // expose a poll function the parent can call (or we self-trigger)
  let attempts = 0;
  function pollAndScroll() {
    const p = getPending();
    if (p.uid && p.at > lastSeenAt) {
      lastSeenAt = p.at;
      tryScroll();
    }
    attempts++;
    if (attempts < 30) setTimeout(pollAndScroll, 100);
  }
  setTimeout(pollAndScroll, 50);
})();
</script>
</body>
</html>
"""


def render_scroll_bridge() -> None:
    """Render the hidden bridge iframe (for scroll behavior) and poll
    `window.cascadePendingNodeId` via streamlit-js-eval.

    Returns: the most recent pending node UID, or None.
    """
    components.html(_BRIDGE_HTML, height=0)


def poll_pending_node(default=None):
    """Poll every ancestor window for `cascadePendingNodeId` and
    `cascadePendingNodeAt`. Returns a JSON string
    `{"uid": "...", "at": 1234567890, "_n": N}` (or default).

    The caller compares `at` against its own last-seen timestamp and re-runs
    when it advances. The `_n` nonce ensures streamlit-js-eval sees a fresh
    value on every poll so it actually re-evaluates.
    """
    import random
    nonce = random.randint(0, 1_000_000_000)
    js = f"""
    (function() {{
      try {{
        // Walk up the parent chain looking for the variable. The DAG and the
        // bridge are in sibling iframes so we need to check all of them.
        let w = window;
        let bestAt = 0;
        let bestUid = null;
        for (let i = 0; i < 10; i++) {{
          if (!w) break;
          try {{
            if (w.cascadePendingNodeAt) {{
              const a = w.cascadePendingNodeAt || 0;
              if (a > bestAt) {{
                bestAt = a;
                bestUid = w.cascadePendingNodeId || null;
              }}
            }}
          }} catch (e) {{}}
          try {{
            if (w.parent && w.parent !== w) w = w.parent;
            else break;
          }} catch (e) {{ break; }}
        }}
        return JSON.stringify({{uid: bestUid, at: bestAt, _n: {nonce}}});
      }} catch (e) {{}}
      return JSON.stringify({{uid: null, at: 0, _n: {nonce}}});
    }})();
    """
    try:
        val = streamlit_js_eval(
            js_expressions=js,
            key="cascade_bridge_poll",
            default=default,
        )
        return val if val is not None else default
    except Exception:
        return default
