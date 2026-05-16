"""FastMCP server exposing list_sources and execute_python tools.

Mounted into the FastAPI app at /mcp. The CompanyStrategyConsultant agent
connects via MCPServerStreamableHttp from inside the same process.
"""

import ast
import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.session import engine
from app.models.source import SourceData

logger = logging.getLogger(__name__)

mcp_app = FastMCP("consultant-tools", streamable_http_path="/")


def _auto_display_last_assignment(code: str) -> str:
    """Append a bare reference to the LHS of the final assignment so it
    auto-displays Jupyter-style — fixes the common LLM mistake of writing
    `result = df.groupby(...).sum()` without a trailing print().

    Skips when the last statement is already an expression, isn't a simple
    Name assignment, or the source can't be parsed.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    if not tree.body:
        return code
    last = tree.body[-1]
    name: str | None = None
    if isinstance(last, ast.Assign) and len(last.targets) == 1 and isinstance(last.targets[0], ast.Name):
        name = last.targets[0].id
    elif isinstance(last, (ast.AugAssign, ast.AnnAssign)) and isinstance(last.target, ast.Name):
        name = last.target.id
    if not name:
        return code
    return code.rstrip() + f"\n{name}\n"


@mcp_app.tool()
def list_sources(workspace_id: int) -> str:
    """List all ready data sources in the given workspace.

    Returns JSON array of {id, title, file_type, original_filename}.
    Use this before execute_python to discover what CSV sources exist
    and choose which to analyze.
    """
    logger.info("[MCP] list_sources(workspace_id=%s)", workspace_id)
    with Session(engine) as db:
        rows = db.exec(
            select(SourceData).where(
                SourceData.workspace_id == workspace_id,
                SourceData.processing_status == "ready",
            )
        ).all()
        payload = json.dumps(
            [
                {
                    "id": s.id,
                    "title": s.title,
                    "file_type": str(s.file_type),
                    "original_filename": s.original_filename,
                }
                for s in rows
            ]
        )
        logger.info("[MCP] list_sources → %d sources: %s", len(rows), payload)
        return payload


@mcp_app.tool()
def execute_python(workspace_id: int, source_ids_json: str, code: str) -> str:
    """Execute Python code against uploaded CSV sources in an isolated E2B sandbox.

    Args:
        workspace_id: Current workspace ID (always pass the workspace_id from
            your system prompt context).
        source_ids_json: JSON list of integer source IDs to load as DataFrames,
            e.g. "[1, 2]". Each CSV is pre-loaded as variable df_<id>.
        code: Python code to run. `pandas` is imported as `pd`. Print results
            or assign to a variable named `result`.

    Returns:
        JSON with `ok: true` and `output: <string>` on success (output combines
        printed lines and the final expression value).
        JSON with `ok: false`, `error: <string>`, and `hint: <string>` on failure.
    """
    from e2b_code_interpreter import Sandbox

    logger.info(
        "[MCP] execute_python(workspace_id=%s, source_ids_json=%r, code_len=%d)",
        workspace_id, source_ids_json, len(code or ""),
    )
    logger.info("[MCP] execute_python code:\n%s", code)

    settings = get_settings()
    if not settings.e2b_api_key:
        logger.warning("[MCP] execute_python: E2B_API_KEY not configured")
        return json.dumps({"error": "E2B_API_KEY not configured"})

    try:
        source_ids = json.loads(source_ids_json)
    except Exception:
        return json.dumps({"error": f"Invalid source_ids_json: {source_ids_json}"})

    with Session(engine) as db:
        sources = db.exec(
            select(SourceData).where(
                SourceData.workspace_id == workspace_id,
                SourceData.file_type == "csv",
                SourceData.processing_status == "ready",
                SourceData.id.in_(source_ids),
            )
        ).all()

        if not sources:
            # Give the agent the current valid IDs so it can self-correct
            # rather than retrying with the same stale values.
            available = db.exec(
                select(SourceData).where(
                    SourceData.workspace_id == workspace_id,
                    SourceData.file_type == "csv",
                    SourceData.processing_status == "ready",
                )
            ).all()
            return json.dumps(
                {
                    "error": (
                        f"No ready CSV sources match source_ids={source_ids} in "
                        f"workspace {workspace_id}. The IDs you passed may be stale "
                        f"from earlier in the conversation. Call list_sources to get "
                        f"current valid IDs, then retry with one of these."
                    ),
                    "current_csv_sources": [
                        {"id": s.id, "title": s.title} for s in available
                    ],
                }
            )

    try:
        with Sandbox.create(api_key=settings.e2b_api_key, timeout=60) as sandbox:
            setup = [
                "import warnings",
                "warnings.filterwarnings('ignore')",
                "import pandas as pd",
            ]
            for s in sources:
                path = Path(s.storage_path)
                if not path.exists():
                    continue
                remote = f"/home/user/{s.id}.csv"
                sandbox.files.write(remote, path.read_bytes())
                setup.append(f'df_{s.id} = pd.read_csv("{remote}")  # {s.title}')

            full_code = "\n".join(setup) + "\n\n" + _auto_display_last_assignment(code)
            execution = sandbox.run_code(full_code)

            stdout = "\n".join(execution.logs.stdout).strip()
            stderr = "\n".join(execution.logs.stderr).strip()

            # E2B surfaces Python exceptions as execution.error (not stderr).
            error_str: str | None = None
            if execution.error:
                error_str = f"{execution.error.name}: {execution.error.value}"
            elif stderr:
                error_str = stderr

            result_value = None
            if execution.results:
                last = execution.results[-1]
                result_value = last.text if hasattr(last, "text") else str(last)

            # Merge stdout + final-cell repr into a single "output" so the LLM
            # has one obvious place to read the answer. Without this it tends
            # to look only at "stdout", see null, and hallucinate failure.
            output_parts: list[str] = []
            if stdout:
                output_parts.append(stdout)
            if result_value and result_value not in output_parts:
                output_parts.append(result_value)
            output = "\n".join(output_parts) if output_parts else None

            loaded = [{"id": s.id, "title": s.title, "variable": f"df_{s.id}"} for s in sources]

            if error_str:
                payload = json.dumps(
                    {
                        "ok": False,
                        "error": error_str,
                        "loaded_sources": loaded,
                        "hint": (
                            f"Use the pre-loaded variables {', '.join(d['variable'] for d in loaded)}; "
                            f"do not call pd.read_csv()."
                        ),
                    }
                )
            else:
                payload = json.dumps(
                    {
                        "ok": True,
                        "output": output or "(code ran successfully but produced no output)",
                        "loaded_sources": loaded,
                    }
                )
            logger.info("[MCP] execute_python → %s", payload[:500])
            return payload
    except Exception as exc:
        logger.warning("[MCP] execute_python E2B/sandbox exception: %r", exc, exc_info=True)
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})
