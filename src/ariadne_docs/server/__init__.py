"""MCP transports for the Ariadne documentation servers.

The open server lives here; the enterprise server is a separate (private)
deployment in ignis-langgraph that imports the same ``ariadne_docs.core`` and
``ariadne_docs.server.tools``.
"""
from .open_server import mcp, run

__all__ = ["mcp", "run"]
