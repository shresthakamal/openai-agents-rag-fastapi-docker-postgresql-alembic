from agents import Agent

chat_agent = Agent(
    name="Chat Agent",
    instructions=(
        "An agent that can chat with the user and answer questions. "
        "You maintain conversation context using the session history provided for each request."
    ),
    tools=[],
    handoffs=[],
    model="gpt-4.1-mini",
)
