"""CODEMAP MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from codemap.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-codemap[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-codemap[mcp]'")
        return 1
    app = FastMCP("codemap")

    @app.tool()
    def codemap_scan(target: str) -> str:
        """Translate and validate medical codes across ICD-10, SNOMED CT, LOINC, RxNorm, and CPT from the CLI.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
