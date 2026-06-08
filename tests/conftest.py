"""
conftest.py — Shared pytest fixtures for Cascade tests.
"""

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"
DEMO_MANIFEST = FIXTURE_DIR / "manifest.json"


@pytest.fixture
def manifest_data() -> dict:
    """Return the parsed demo manifest.json as a dict."""
    with open(DEMO_MANIFEST, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def manifest_path() -> Path:
    """Return the path to the demo manifest.json fixture."""
    return DEMO_MANIFEST
