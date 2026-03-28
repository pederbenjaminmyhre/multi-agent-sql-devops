import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage

_PROMPT_PATH = Path(__file__).parent / "prompts" / "doc_genie_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def run_doc_genie(llm, sql: str) -> dict:
    """Invoke the Doc-Genie agent. Returns {documentation, extended_properties_sql}."""
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Generate documentation for any new objects in this T-SQL:\n\n```sql\n{sql}\n```"
        ),
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
            "documentation": "",
            "extended_properties_sql": [],
        }

    return {
        "documentation": data.get("documentation", ""),
        "extended_properties_sql": data.get("extended_properties_sql", []),
    }
