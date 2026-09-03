"""LangGraph wiring for the Denominator agent pipeline.

Each of the 5 agents becomes a node. Edges run them in a straight line for
now: Ingestion -> Product Identity -> Regulatory Context -> Scope
Validation -> Document Impact. Later days add the rate engine and the
human decision gate in between Scope Validation and Document Impact.

Nodes are placeholders today (the agents themselves raise
NotImplementedError), so each node wrapper catches that specifically and
records it as a pending step rather than crashing the graph. This lets the
graph compile and run end-to-end right now, so the *shape* of the pipeline
can be reviewed before any agent has real logic.
"""

from langgraph.graph import END, StateGraph

from .agent1_maude_ingestion import MaudeIngestionAgent
from .agent2_product_identity import ProductIdentityAgent
from .agent3_regulatory_context import RegulatoryContextAgent
from .agent4_scope_validation import ScopeValidationAgent
from .agent5_document_impact import DocumentImpactAgent
from .state import PipelineState


def _run_agent_node(agent, result_key: str):
    """Wrap a DenominatorAgent as a LangGraph node function."""

    def node(state: PipelineState) -> PipelineState:
        errors = list(state.get("errors", []))
        try:
            result = agent.run(state.get("inputs", {}))
            state[result_key] = result.output
        except NotImplementedError as exc:
            errors.append(f"{agent.name}: not yet implemented ({exc})")
            state[result_key] = {"status": "pending", "reason": str(exc)}
        state["errors"] = errors
        return state

    return node


def build_pipeline_graph(cache_manager=None):
    """Construct and compile the Denominator agent pipeline graph."""

    graph = StateGraph(PipelineState)

    graph.add_node("maude_ingestion", _run_agent_node(
        MaudeIngestionAgent(cache_manager), "maude_ingestion_result"))
    graph.add_node("product_identity", _run_agent_node(
        ProductIdentityAgent(cache_manager), "product_identity_result"))
    graph.add_node("regulatory_context", _run_agent_node(
        RegulatoryContextAgent(cache_manager), "regulatory_context_result"))
    graph.add_node("scope_validation", _run_agent_node(
        ScopeValidationAgent(cache_manager), "scope_validation_result"))
    graph.add_node("document_impact", _run_agent_node(
        DocumentImpactAgent(cache_manager), "document_impact_result"))

    graph.set_entry_point("maude_ingestion")
    graph.add_edge("maude_ingestion", "product_identity")
    graph.add_edge("product_identity", "regulatory_context")
    graph.add_edge("regulatory_context", "scope_validation")
    graph.add_edge("scope_validation", "document_impact")
    graph.add_edge("document_impact", END)

    return graph.compile()


if __name__ == "__main__":
    pipeline = build_pipeline_graph()
    final_state = pipeline.invoke({"inputs": {}, "errors": []})
    for key, value in final_state.items():
        print(f"{key}: {value}")
