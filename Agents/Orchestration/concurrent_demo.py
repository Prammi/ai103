import asyncio
import os

from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import ConcurrentBuilder
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


async def main():
    # ---------------------------------------------------------
    # Load configuration
    # ---------------------------------------------------------
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5-mini")

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    print("\n=== CONCURRENT ORCHESTRATION DEMO ===\n")
    print(f"Model: {model_deployment}")

    # ---------------------------------------------------------
    # Create Foundry chat client
    # ---------------------------------------------------------
    chat_client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model_deployment,
        credential=DefaultAzureCredential(),
    )

    # ---------------------------------------------------------
    # Agent 1 - IT Agent
    # ---------------------------------------------------------
    it_agent = chat_client.as_agent(
        name="it_agent",
        instructions=(
            "You are an IT support agent. "
            "The user will describe a situation. "
            "Respond only with IT-related considerations. "
            "Keep your response to 2 short sentences."
        ),
    )

    # ---------------------------------------------------------
    # Agent 2 - HR Agent
    # ---------------------------------------------------------
    hr_agent = chat_client.as_agent(
        name="hr_agent",
        instructions=(
            "You are an HR support agent. "
            "The user will describe a situation. "
            "Respond only with HR-related considerations. "
            "Keep your response to 2 short sentences."
        ),
    )

    # ---------------------------------------------------------
    # Concurrent workflow
    #
    #              ┌──> IT Agent
    # User Input ──┤
    #              └──> HR Agent
    #
    # Both receive the SAME original input.
    # ---------------------------------------------------------
    workflow = ConcurrentBuilder(
        participants=[
            it_agent,
            hr_agent,
        ]
    ).build()

    # ---------------------------------------------------------
    # User input
    # ---------------------------------------------------------
    question = (
        "I am relocating to Germany for work. "
        "What should I consider?"
    )

    print("\nUSER:")
    print(question)

    print("\n--- WORKFLOW STARTED ---\n")

    # ---------------------------------------------------------
    # Run workflow
    # ---------------------------------------------------------
    async for event in workflow.run(question, stream=True):

        if event.type == "output":
            output = event.data

            if getattr(output, "text", None):
                print(output.text)

    print("\n--- WORKFLOW COMPLETED ---")


if __name__ == "__main__":
    asyncio.run(main())