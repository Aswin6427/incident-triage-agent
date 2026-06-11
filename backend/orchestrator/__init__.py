# Lazy imports — graph pulls in agents+LLM so we only load on demand
__all__ = ["build_triage_graph", "IncidentState"]


def build_triage_graph():
    from .graph import build_triage_graph as _build
    return _build()


from .state import IncidentState  # noqa: E402 (state has no heavy deps)
