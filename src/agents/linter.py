import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from src.models.agent_finding import AgentFinding, Severity
from src.tools.sql_formatter import SQL_FORMAT_TOOLS

_PROMPT_PATH = Path(__file__).parent / "prompts" / "linter_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def run_linter(llm, sql: str) -> dict:
    """Invoke the Linter agent. Returns {findings, cleaned_sql}."""
    llm_with_tools = llm.bind_tools(SQL_FORMAT_TOOLS)
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Review this T-SQL script:\n\n```sql\n{sql}\n```"),
    ]
    response = llm_with_tools.invoke(messages)
    return _parse_response(response)


def _parse_response(response) -> dict:
    try:
        content = response.content
        # Strip markdown fences if present
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
            severity=Severity(f.get("severity", "info")),
            agent="linter",
            message=f.get("message", ""),
            line_ref=f.get("line_ref"),
            suggestion=f.get("suggestion"),
        )
        for f in data.get("findings", [])
    ]
    return {
        "findings": findings,
        "cleaned_sql": data.get("cleaned_sql", ""),
    }
