from langgraph.graph import StateGraph, END
from src.graph.state import ReviewState
from src.graph.nodes import (
    linter_node,
    performance_node,
    doc_genie_node,
    skeptic_node,
    report_node,
)
from src.graph.edges import route_after_skeptic


def build_review_graph() -> StateGraph:
    """Construct and compile the multi-agent review state graph."""
    graph = StateGraph(ReviewState)

    # Add nodes
    graph.add_node("linter_node", linter_node)
    graph.add_node("performance_node", performance_node)
    graph.add_node("doc_genie_node", doc_genie_node)
    graph.add_node("skeptic_node", skeptic_node)
    graph.add_node("report_node", report_node)

    # Linear flow: linter -> performance -> doc_genie -> skeptic
    graph.set_entry_point("linter_node")
    graph.add_edge("linter_node", "performance_node")
    graph.add_edge("performance_node", "doc_genie_node")
    graph.add_edge("doc_genie_node", "skeptic_node")

    # Conditional: skeptic -> linter (rejected) or report (approved)
    graph.add_conditional_edges(
        "skeptic_node",
        route_after_skeptic,
        {
            "linter_node": "linter_node",
            "report_node": "report_node",
        },
    )

    # Report -> END
    graph.add_edge("report_node", END)

    return graph.compile()
