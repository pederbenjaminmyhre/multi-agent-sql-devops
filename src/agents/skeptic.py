import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from src.models.agent_finding import AgentFinding, Severity
from src.tools.schema_checker import SCHEMA_TOOLS

_PROMPT_PATH = Path(__file__).parent / "prompts" / "skeptic_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def run_skeptic(
    llm,
    original_sql: str,
    cleaned_sql: str,
    findings: list[AgentFinding],
    index_suggestions: list[str],
) -> dict:
    """Invoke the Skeptic/Validator agent. Returns {verdict, reasoning, issues}."""
    llm_with_tools = llm.bind_tools(SCHEMA_TOOLS)

    findings_text = "\n".join(
        f"- [{f.severity.value}] {f.message}" + (f" (suggestion: {f.suggestion})" if f.suggestion else "")
        for f in findings
    )
    index_text = "\n".join(index_suggestions) if index_suggestions else "None"

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"## Original SQL\n```sql\n{original_sql}\n```\n\n"
            f"## Proposed Cleaned SQL\n```sql\n{cleaned_sql}\n```\n\n"
            f"## Findings from Linter & Performance Critic\n{findings_text}\n\n"
            f"## Suggested Indexes\n```sql\n{index_text}\n```\n\n"
            "Validate whether these changes are safe to apply."
        )),
    ]
    response = llm_with_tools.invoke(messages)
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
            severity=Severity(i.get("severity", "warning")),
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
