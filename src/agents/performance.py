import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from src.models.agent_finding import AgentFinding, Severity, normalize_severity
from src.tools.schema_checker import load_schema

_PROMPT_PATH = Path(__file__).parent / "prompts" / "performance_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def run_performance(llm, sql: str, schema_context: dict | None = None) -> dict:
    """Invoke the Performance Critic agent. Returns {findings, index_suggestions}."""
    schema = schema_context or load_schema()
    schema_summary = _build_schema_summary(schema)

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Analyze this T-SQL for performance issues:\n\n```sql\n{sql}\n```\n\n"
                f"## Schema Dictionary\n```\n{schema_summary}\n```"
            )
        ),
    ]
    response = llm.invoke(messages)
    return _parse_response(response)


def _build_schema_summary(schema: dict) -> str:
    """Build a human-readable schema summary for the LLM prompt."""
    lines = []
    for table_name, table in schema.get("tables", {}).items():
        cols = ", ".join(
            f"{c} ({info['type']})" for c, info in table.get("columns", {}).items()
        )
        lines.append(f"TABLE {table_name}: {cols}")
        for ix in table.get("indexes", []):
            tag = "UNIQUE " if ix["is_unique"] else ""
            lines.append(f"  INDEX {ix['name']}: {tag}({', '.join(ix['columns'])})")
        for fk in table.get("foreign_keys", []):
            lines.append(
                f"  FK {fk['column']} -> {fk['references']['table']}.{fk['references']['column']}"
            )
    return "\n".join(lines)


def _parse_response(response) -> dict:
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        data = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        return {
            "findings": [
                AgentFinding(
                    severity=Severity.WARNING,
                    agent="performance",
                    message="Performance agent returned unparseable output.",
                )
            ],
            "index_suggestions": [],
        }

    findings = [
        AgentFinding(
            severity=normalize_severity(f.get("severity", "info")),
            agent="performance",
            message=f.get("message", ""),
            line_ref=str(f["line_ref"]) if f.get("line_ref") is not None else None,
            suggestion=f.get("suggestion"),
        )
        for f in data.get("findings", [])
    ]
    return {
        "findings": findings,
        "index_suggestions": data.get("index_suggestions", []),
    }
