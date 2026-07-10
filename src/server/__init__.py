"""Server package — MCP layer."""
from .registry import (
    mcp,
    get_app,
    run_stdio,
    get_pool,
)

__all__ = ["mcp", "get_app", "run_stdio", "get_pool"]
