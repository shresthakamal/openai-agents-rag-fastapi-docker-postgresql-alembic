from agents import Agent, ModelSettings

SYSTEM_INSTRUCTION = (
    "An agent that can chat with the user and answer questions. "
    "You maintain conversation context using the session history provided for each request."
)

chat_agent = Agent(
    name="Chat Agent",
    instructions=SYSTEM_INSTRUCTION,
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
