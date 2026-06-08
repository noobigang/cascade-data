"""URL state encoder/decoder for shareable Cascade views.

Encodes the current DAG view state (selected node, physics toggle, filters)
into a compact base64 URL param so users can share a link to a specific view.
Decodes on load to restore the view state.
"""

import base64
import json
import zlib


def encode_state(state: dict) -> str:
    """
    Encode a view state dict into a URL-safe base64 string.

    Args:
        state: Dict with keys like:
            - selected_node (str): selected model node ID
            - physics_enabled (bool): physics toggle
            - filters (dict): resource type filters
            - zoom (float): zoom level
            - center (list): [x, y] pan offset

    Returns:
        A compact base64-encoded string suitable for URL params.
    """
    if not state:
        return ""

    # Compress the JSON for shorter URLs
    json_str = json.dumps(state, sort_keys=True)
    compressed = zlib.compress(json_str.encode("utf-8"), level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    # Strip trailing = padding for cleaner URLs
    return encoded.rstrip("=")


def decode_state(encoded: str) -> dict | None:
    """
    Decode a URL-safe base64 string back to a view state dict.

    Args:
        encoded: The base64-encoded state string from the URL.

    Returns:
        The decoded state dict, or None if decoding fails.
    """
    if not encoded:
        return None

    try:
        # Restore padding
        padded = encoded + "=" * (4 - len(encoded) % 4)
        compressed = base64.urlsafe_b64decode(padded)
        json_str = zlib.decompress(compressed).decode("utf-8")
        return json.loads(json_str)  # type: ignore[no-any-return]
    except Exception:
        # Silently fail on invalid state — user just gets the default view
        return None


def build_share_url(base_url: str, state: dict) -> str:
    """
    Build a full shareable URL with encoded state as a query param.

    Args:
        base_url: The app's base URL.
        state: The view state to encode.

    Returns:
        A full URL string with ?state=<encoded>.
    """
    if not state:
        return base_url

    encoded = encode_state(state)
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}state={encoded}"


def extract_state_from_url(query_params: dict) -> dict | None:
    """
    Extract and decode state from a Streamlit query_params dict.

    Args:
        query_params: st.experimental_get_query_params() result.

    Returns:
        Decoded state dict, or None.
    """
    state_list = query_params.get("state", [])
    if not state_list:
        return None
    return decode_state(state_list[0])


def build_state_from_session(dag, selected_node, physics_enabled, filters) -> dict:
    """
    Build a serializable state dict from the current session.

    Args:
        dag: NetworkX DiGraph (for metadata only)
        selected_node: Currently selected node ID
        physics_enabled: Physics toggle bool
        filters: Dict of filter states

    Returns:
        A state dict ready for encoding.
    """
    return {
        "selected_node": selected_node,
        "physics_enabled": physics_enabled,
        "filters": filters,
        "node_count": len(dag.nodes) if dag else 0,
    }
