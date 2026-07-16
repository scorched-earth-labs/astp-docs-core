"""ariadne-docs — retrieval core + open documentation MCP server.

One engine, two physically isolated corpora (open protocol / enterprise
Ignis-OS), several transports (MCP, web chat). This package holds the shared
core and the *open* server; the enterprise server lives privately in
ignis-langgraph and depends on this core as a package.
"""
__version__ = "0.1.0"
