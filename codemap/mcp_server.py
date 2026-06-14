"""CODEMAP MCP server — exposes validate/crosswalk as MCP tools for Cognis.Studio."""
from __future__ import annotations
import json
from codemap.core import validate_code, crosswalk, CodeSystem


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
    def codemap_validate(code: str) -> str:
        """Validate a medical code (ICD-10, LOINC, RxNorm, CPT). Returns JSON."""
        result = validate_code(code)
        return json.dumps(result.as_dict())

    @app.tool()
    def codemap_crosswalk(code: str, target_system: str = "") -> str:
        """Crosswalk a medical code to mapped concepts. Returns JSON list."""
        target = None
        if target_system:
            try:
                target = CodeSystem(target_system.strip().upper().replace("-", ""))
            except ValueError:
                return json.dumps({"error": f"unknown system: {target_system!r}"})
        results = crosswalk(code, target)
        return json.dumps([r.as_dict() for r in results])

    app.run()
    return 0
