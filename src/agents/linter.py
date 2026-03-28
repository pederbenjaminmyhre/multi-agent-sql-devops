import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from src.models.agent_finding import AgentFinding, Severity, normalize_severity
from src.tools.sql_formatter import format_sql

_PROMPT_PATH = Path(__file__).parent / "prompts" / "linter_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def run_linter(llm, sql: str) -> dict:
    """Invoke the Linter agent. Returns {findings, cleaned_sql}."""
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Review this T-SQL script:\n\n```sql\n{sql}\n```"),
    ]
    response = llm.invoke(messages)
    result = _parse_response(response)
    # Apply SQL formatter tool to the cleaned SQL if present
    if result["cleaned_sql"]:
        result["cleaned_sql"] = format_sql.invoke({"sql": result["cleaned_sql"]})
    return result


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
                    agent="linter",
                    message="Linter returned unparseable output.",
                )
            ],
            "cleaned_sql": "",
        }

    findings = [
        AgentFinding(
            severity=normalize_severity(f.get("severity", "info")),
            agent="linter",
            message=f.get("message", ""),
            line_ref=str(f["line_ref"]) if f.get("line_ref") is not None else None,
            suggestion=f.get("suggestion"),
        )
        for f in data.get("findings", [])
    ]
    return {
        "findings": findings,
        "cleaned_sql": data.get("cleaned_sql", ""),
    }
