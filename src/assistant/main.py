from agents import Agent, ModelSettings

from assistant.tools import search_knowledge_base
from prompts.loader import ASSISTANT_SYSTEM

assistant_agent = Agent(
    name="General Assistant",
    instructions=ASSISTANT_SYSTEM,
    tools=[search_knowledge_base],
    model_settings=ModelSettings(
        model="gpt-4.1-mini",
        temperature=0.0,
        max_tokens=1000,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=None,
        logprobs=None,
        logit_bias=None,
    ),
)
