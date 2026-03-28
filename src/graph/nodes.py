from src.graph.state import ReviewState
from src.agents.linter import run_linter
from src.agents.performance import run_performance
from src.agents.doc_genie import run_doc_genie
from src.agents.skeptic import run_skeptic
from src.tools.changelog_writer import build_changelog
from src.models.agent_finding import AgentFinding


def get_llm():
    from src.config import settings
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
        )


def linter_node(state: ReviewState) -> dict:
    llm = get_llm()
    sql = state.get("cleaned_sql") or state["sql_input"]
    result = run_linter(llm, sql)
    iteration = state.get("iteration", 0) + 1
    entries = list(state.get("changelog_entries", []))
    for f in result["findings"]:
        entries.append(f"[Linter pass {iteration}] {f.message}")
    return {
        "linter_findings": result["findings"],
        "cleaned_sql": result["cleaned_sql"] or sql,
        "iteration": iteration,
        "changelog_entries": entries,
    }


def performance_node(state: ReviewState) -> dict:
    llm = get_llm()
    sql = state.get("cleaned_sql", state["sql_input"])
    result = run_performance(llm, sql, state.get("schema_context"))
    entries = list(state.get("changelog_entries", []))
    for f in result["findings"]:
        entries.append(f"[Performance] {f.message}")
    return {
        "performance_findings": result["findings"],
        "index_suggestions": result["index_suggestions"],
        "changelog_entries": entries,
    }


def doc_genie_node(state: ReviewState) -> dict:
    llm = get_llm()
    sql = state.get("cleaned_sql", state["sql_input"])
    result = run_doc_genie(llm, sql)
    return {
        "documentation": result["documentation"],
        "extended_properties_sql": result["extended_properties_sql"],
    }


def skeptic_node(state: ReviewState) -> dict:
    llm = get_llm()
    all_findings: list[AgentFinding] = list(state.get("linter_findings", []))
    all_findings.extend(state.get("performance_findings", []))
    result = run_skeptic(
        llm,
        original_sql=state["sql_input"],
        cleaned_sql=state.get("cleaned_sql", ""),
        findings=all_findings,
        index_suggestions=state.get("index_suggestions", []),
        schema_context=state.get("schema_context"),
    )
    entries = list(state.get("changelog_entries", []))
    entries.append(f"[Skeptic] Verdict: {result['verdict']} — {result['reasoning']}")
    return {
        "skeptic_verdict": result["verdict"],
        "skeptic_reasoning": result["reasoning"],
        "skeptic_issues": result["issues"],
        "changelog_entries": entries,
    }


def report_node(state: ReviewState) -> dict:
    all_findings: list[AgentFinding] = list(state.get("linter_findings", []))
    all_findings.extend(state.get("performance_findings", []))
    all_findings.extend(state.get("skeptic_issues", []))

    changelog_md = build_changelog(state.get("changelog_entries", []))

    report = {
        "status": state.get("skeptic_verdict", "approved"),
        "iterations": state.get("iteration", 1),
        "findings": [f.model_dump() for f in all_findings],
        "cleaned_sql": state.get("cleaned_sql", state["sql_input"]),
        "documentation": state.get("documentation", ""),
        "changelog": changelog_md,
    }
    return {"final_report": report}
