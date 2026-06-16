from typing import Any

from agents import Agent, RunHooks
from agents.run_context import AgentHookContext

from utils.logging import get_logger

logger = get_logger(__name__)


class LoggingHooks(RunHooks):
    async def on_agent_start(self, context, agent: Agent) -> None:
        logger.info("Starting %s", agent.name)

    async def on_llm_end(self, context, agent: Agent, response) -> None:
        logger.info("%s produced %d output items", agent.name, len(response.output))

    async def on_agent_end(self, context, agent: Agent, output: Any) -> None:
        logger.info("%s finished with usage: %s", agent.name, context.usage)

    async def on_tool_start(self, context, agent: Agent, tool) -> None:
        logger.info("%s calling tool: %s", agent.name, tool.name)

    async def on_tool_end(self, context, agent: Agent, tool, result) -> None:
        logger.info("%s finished tool: %s", agent.name, tool.name)


class UsageHooks(RunHooks):
    async def on_agent_end(
        self,
        context: AgentHookContext,
        agent: Agent,
        output: Any,
    ) -> None:
        usage = context.usage
        logger.info(
            "%s → %s requests, %s total tokens",
            agent.name,
            usage.requests,
            usage.total_tokens,
        )


class CombinedRunHooks(RunHooks):
    def __init__(self, *hooks: RunHooks) -> None:
        self._hooks = hooks

    async def _invoke(self, method_name: str, *args, **kwargs) -> None:
        for hook in self._hooks:
            await getattr(hook, method_name)(*args, **kwargs)

    async def on_agent_start(self, context, agent: Agent) -> None:
        await self._invoke("on_agent_start", context, agent)

    async def on_agent_end(self, context, agent: Agent, output: Any) -> None:
        await self._invoke("on_agent_end", context, agent, output)

    async def on_llm_start(self, context, agent: Agent, system_prompt, input_items) -> None:
        await self._invoke("on_llm_start", context, agent, system_prompt, input_items)

    async def on_llm_end(self, context, agent: Agent, response) -> None:
        await self._invoke("on_llm_end", context, agent, response)

    async def on_tool_start(self, context, agent: Agent, tool) -> None:
        await self._invoke("on_tool_start", context, agent, tool)

    async def on_tool_end(self, context, agent: Agent, tool, result) -> None:
        await self._invoke("on_tool_end", context, agent, tool, result)

    async def on_handoff(self, context, from_agent: Agent, to_agent: Agent) -> None:
        await self._invoke("on_handoff", context, from_agent, to_agent)


logging_hooks = LoggingHooks()
usage_hooks = UsageHooks()

run_hooks = CombinedRunHooks(logging_hooks, usage_hooks)
