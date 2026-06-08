"""Share card — URL state sharing and PNG export for Cascade DAG."""


import streamlit as st
import streamlit.components.v1 as components

from cascade.utils.state_encoder import build_state_from_session, encode_state


def render_share_card(
    dag,
    selected_node: str | None,
    physics_enabled: bool,
    filters: dict | None = None,
) -> None:
    """
    Render the share card UI: copy shareable link + download PNG.

    Args:
        dag: NetworkX DiGraph (for state metadata).
        selected_node: Currently selected node ID.
        physics_enabled: Physics toggle state.
        filters: Dict of resource type filter states.
    """
    if dag is None or len(dag.nodes) == 0:
        return

    filters = filters or {}

    # Build state
    state = build_state_from_session(dag, selected_node, physics_enabled, filters)
    encoded = encode_state(state)

    # Build the shareable URL (uses current page as base)
    # In Streamlit Cloud, this will be the deployed URL
    try:
        # Attempt to get the current page URL from query params
        query_params = st.query_params  # type: ignore[attr-defined]
        base = query_params.get("_stcore_url", [""])[0] or "https://cascade-data.hf.space"
    except Exception:
        base = "https://cascade-data.hf.space"

    share_url = f"{base}?state={encoded}"

    # Shorten display URL
    display_url = share_url[:80] + "..." if len(share_url) > 80 else share_url

    # ── Share URL card ────────────────────────────────────────────────────────
    st.markdown("#### 🔗 Share This View")

    col_url, col_copy = st.columns([4, 1])

    with col_url:
        st.code(display_url, language=None, wrap_lines=True)

    with col_copy:
        # Copy button via HTML/JS
        _render_copy_button(share_url)

    st.caption(
        "Share this link to let others see the same DAG view — "
        "no login required."
    )

    st.divider()

    # ── Download PNG card ──────────────────────────────────────────────────────
    st.markdown("#### 📷 Export as PNG")

    st.markdown(
        """
        <div style="
            background: #161B22;
            border: 1px solid #30363D;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        ">
            <p style="
                color: #8B949E;
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                margin: 0 0 8px 0;
            ">
                To download the DAG as PNG:
            </p>
            <ol style="
                color: #E6EDF3;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                margin: 0;
                padding-left: 20px;
            ">
                <li>Click the <strong style="color: #58A6FF;">camera</strong> icon in the DAG toolbar (bottom-right)</li>
                <li>The graph will open in a new tab as a PNG</li>
                <li>Right-click → <strong>Save image as…</strong></li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Also provide a direct download via JS canvas capture if PyVis is in an iframe
    # This is a fallback: we expose the download via a custom HTML button
    # that triggers the PyVis camera capture
    _render_png_download_script()


def _render_copy_button(url: str) -> None:
    """Render a copy-to-clipboard button using HTML/JS."""
    escaped = url.replace("'", "\\'").replace("\n", "\\n")
    components.html(
        f"""
        <script>
        async function copyLink() {{
            try {{
                await navigator.clipboard.writeText('{escaped}');
                const btn = document.getElementById('copy-btn');
                btn.textContent = '✅ Copied!';
                btn.style.background = '#39D353';
                btn.style.color = '#0D1117';
                setTimeout(() => {{
                    btn.textContent = '📋 Copy';
                    btn.style.background = '';
                    btn.style.color = '';
                }}, 2000);
            }} catch (e) {{
                const btn = document.getElementById('copy-btn');
                btn.textContent = '❌ Error';
            }}
        }}
        </script>
        <button
            id="copy-btn"
            onclick="copyLink()"
            style="
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                color: #58A6FF;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                cursor: pointer;
                transition: all 150ms ease-out;
                white-space: nowrap;
                width: 100%;
                height: 38px;
            "
            onmouseover="this.style.borderColor='#58A6FF'; this.style.boxShadow='0 0 8px rgba(88,166,255,0.3)';"
            onmouseout="this.style.borderColor='#30363D'; this.style.boxShadow='none';"
        >
            📋 Copy
        </button>
        """,
        height=50,
        scrolling=False,
    )


def _render_png_download_script() -> None:
    """Render an inline script that exposes the PyVis PNG download to Streamlit."""
    components.html(
        """
        <script>
        // Find the PyVis canvas and trigger download via canvas API
        function downloadDAGasPNG() {
            const canvas = document.querySelector('#network canvas');
            if (!canvas) {
                alert('DAG canvas not found. Please use the camera button in the DAG toolbar.');
                return;
            }
            const link = document.createElement('a');
            link.download = 'cascade-lineage.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        }
        </script>
        <style>
        #download-dag-btn {
            background: #161B22;
            border: 1px solid #30363D;
            border-radius: 6px;
            color: #58A6FF;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            font-weight: 600;
            padding: 8px 16px;
            cursor: pointer;
            transition: all 150ms ease-out;
            width: 100%;
            margin-top: 4px;
        }
        #download-dag-btn:hover {
            border-color: #58A6FF;
            box-shadow: 0 0 12px rgba(88,166,255,0.3);
            background: #21262D;
        }
        </style>
        """,
        height=0,
        scrolling=False,
    )
