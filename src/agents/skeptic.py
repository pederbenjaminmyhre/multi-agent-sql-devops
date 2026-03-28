import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from src.models.agent_finding import AgentFinding, Severity, normalize_severity
from src.tools.schema_checker import load_schema

_PROMPT_PATH = Path(__file__).parent / "prompts" / "skeptic_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def run_skeptic(
    llm,
    original_sql: str,
    cleaned_sql: str,
    findings: list[AgentFinding],
    index_suggestions: list[str],
    schema_context: dict | None = None,
) -> dict:
    """Invoke the Skeptic/Validator agent. Returns {verdict, reasoning, issues}."""
    schema = schema_context or load_schema()

    findings_text = "\n".join(
        f"- [{f.severity.value}] {f.message}" + (f" (suggestion: {f.suggestion})" if f.suggestion else "")
        for f in findings
    )
    index_text = "\n".join(index_suggestions) if index_suggestions else "None"

    # Build a brief schema summary for context
    schema_lines = []
    for tbl, info in schema.get("tables", {}).items():
        ixs = ", ".join(ix["name"] for ix in info.get("indexes", []))
        fks = ", ".join(f"{fk['column']}->{fk['references']['table']}" for fk in info.get("foreign_keys", []))
        schema_lines.append(f"{tbl}: indexes=[{ixs}] fks=[{fks}]")
    schema_summary = "\n".join(schema_lines)

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"## Original SQL\n```sql\n{original_sql}\n```\n\n"
            f"## Proposed Cleaned SQL\n```sql\n{cleaned_sql}\n```\n\n"
            f"## Findings from Linter & Performance Critic\n{findings_text}\n\n"
            f"## Suggested Indexes\n```sql\n{index_text}\n```\n\n"
            f"## Schema Context\n```\n{schema_summary}\n```\n\n"
            "Validate whether these changes are safe to apply."
        )),
    ]
    response = llm.invoke(messages)
    return _parse_response(response)


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
            "verdict": "approved",
            "reasoning": "Skeptic returned unparseable output; defaulting to approved.",
            "issues": [],
        }

    issues = [
        AgentFinding(
            severity=normalize_severity(i.get("severity", "warning")),
            agent="skeptic",
            message=i.get("message", ""),
        )
        for i in data.get("issues", [])
    ]
    return {
        "verdict": data.get("verdict", "approved"),
        "reasoning": data.get("reasoning", ""),
        "issues": issues,
    }
