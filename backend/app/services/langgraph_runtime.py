from collections.abc import AsyncIterator
from typing import Protocol, TypedDict

from langgraph.graph import END, START, StateGraph


class AgentRuntime(Protocol):
    def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]: ...


class WorkflowState(TypedDict):
    requirement: str
    model: str
    response_instructions: str
    architect_prompt: str


class LangGraphRuntime:
    """Prepare one focused architecture call instead of streaming duplicate agent drafts."""

    def __init__(self, agent_runtime: AgentRuntime) -> None:
        self._agent_runtime = agent_runtime
        graph = StateGraph(WorkflowState)
        graph.add_node("prepare", self._prepare_architecture)
        graph.add_edge(START, "prepare")
        graph.add_edge("prepare", END)
        self._graph = graph.compile()

    async def _prepare_architecture(self, state: WorkflowState) -> dict[str, str]:
        return {
            "architect_prompt": (
                f"Requirement:\n{state['requirement']}\n\n"
                "Create the final architecture proposal directly. Prioritize concrete decisions, "
                "security, data integrity, failure handling, and tests. Be concise: avoid "
                "repeating "
                "the requirement, avoid filler, and keep each requested section brief. State "
                "assumptions and include an explicit human approval checkpoint before "
                "implementation."
            )
        }

    async def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        state = None
        async for next_state in self._graph.astream(
            {
                "requirement": prompt,
                "model": model,
                "response_instructions": system_prompt,
            },
            stream_mode="values",
        ):
            state = next_state
        assert state is not None
        yield "## Architecture proposal\n\n"
        async for token in self._agent_runtime.stream(
            prompt=state["architect_prompt"],
            model=model,
            system_prompt=("You are the Architect agent. " + state["response_instructions"]),
        ):
            yield token
