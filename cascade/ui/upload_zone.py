"""Drag-and-drop manifest.json upload widget."""

import json

import streamlit as st


class UploadZone:
    """Drag-and-drop upload zone for manifest.json files."""

    def __init__(self):
        self.manifest = None

    def render(self) -> dict | None:
        """
        Render the upload widget and return the parsed manifest dict.
        Returns None if no file uploaded yet.
        """
        st.markdown("### Upload manifest.json")
        st.markdown(
            "Upload your dbt `target/manifest.json` to start exploring lineage."
        )

        uploaded_file = st.file_uploader(
            label="Drag & drop or click to upload",
            type=["json"],
            help="Upload the manifest.json from your dbt project's `target/` directory.",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            try:
                content = uploaded_file.read()
                manifest = json.loads(content.decode("utf-8"))

                # Show file info
                size_kb = len(content) / 1024
                st.success(f"✅ Loaded: `{uploaded_file.name}` ({size_kb:.1f} KB)")

                # Basic validation
                if "nodes" not in manifest:
                    st.error("❌ Invalid manifest.json — missing 'nodes' key.")
                    return None

                node_count = len(manifest.get("nodes", {}))
                st.caption(f"📦 {node_count:,} nodes parsed")

                self.manifest = manifest
                return manifest  # type: ignore[no-any-return]

            except json.JSONDecodeError as e:
                st.error(f"❌ Failed to parse JSON: {e}")
                return None

        return None
