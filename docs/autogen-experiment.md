# Experimental AutoGen bridge

ArchitectAI uses Microsoft AutoGen AgentChat 0.7.5 as an isolated model runtime. AutoGen is
archived and no longer maintained by Microsoft, so it is not treated as a
permanent production dependency. The maintained successor is Microsoft Agent Framework.

Official references:

- [AutoGen repository and archive notice](https://github.com/microsoft/autogen)
- [AutoGen native Ollama client](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/models.html#ollama)
- [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/)

## Local configuration

The bridge uses `autogen-agentchat` and `autogen-ext[ollama]` with the native
`OllamaChatCompletionClient`. It talks only to `OLLAMA_BASE_URL` and uses the configured local
model. No API key or Azure subscription is required.

`AUTOGEN_EXPERIMENTAL_ENABLED=true` routes model execution through an AutoGen `AssistantAgent`.
With `LANGGRAPH_ORCHESTRATION_ENABLED=true`, LangGraph prepares the architecture request before
the single Architect model call. Disable LangGraph to use AutoGen directly; disable both flags
to return to the direct model provider.

No tools, workbenches, command-line executors, or generated-code execution are registered.
The bridge is intentionally hidden behind ArchitectAI's `AgentRuntime` protocol so it can be
removed or migrated without changing the dashboard, persistence, or SSE contracts.

Diagnostic endpoint:

```text
GET /api/v1/autogen/status
```

