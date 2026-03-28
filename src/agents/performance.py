import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from src.models.agent_finding import AgentFinding, Severity
from src.tools.schema_checker import SCHEMA_TOOLS

_PROMPT_PATH = Path(__file__).parent / "prompts" / "performance_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def run_performance(llm, sql: str, schema_context: dict | None = None) -> dict:
    """Invoke the Performance Critic agent. Returns {findings, index_suggestions}."""
    llm_with_tools = llm.bind_tools(SCHEMA_TOOLS)
    schema_note = ""
    if schema_context:
        schema_note = f"\n\nSchema context provided:\n```json\n{json.dumps(schema_context, indent=2)}\n```"

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Analyze this T-SQL for performance issues:\n\n```sql\n{sql}\n```{schema_note}"
        ),
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
            severity=Severity(f.get("severity", "info")),
            agent="performance",
            message=f.get("message", ""),
            line_ref=f.get("line_ref"),
            suggestion=f.get("suggestion"),
        )
        for f in data.get("findings", [])
    ]
    return {
        "findings": findings,
        "index_suggestions": data.get("index_suggestions", []),
    }
