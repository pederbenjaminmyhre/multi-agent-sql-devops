from src.graph.state import ReviewState


def route_after_skeptic(state: ReviewState) -> str:
    """Decide whether to loop back to the linter or proceed to the report."""
    verdict = state.get("skeptic_verdict", "approved")
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 3)

    if verdict == "rejected" and iteration < max_iter:
        return "linter_node"
    return "report_node"
