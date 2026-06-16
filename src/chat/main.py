from agents import Agent, ModelSettings

from prompts.loader import CHAT_SYSTEM

chat_agent = Agent(
    name="Chat Agent",
    instructions=CHAT_SYSTEM,
    tools=[],
    handoffs=[],
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
