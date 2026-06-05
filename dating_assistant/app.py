from __future__ import annotations

from src.app_core import generate


def create_result(request):
    """Small hook for a future Streamlit/Web UI."""
    return generate(request)

