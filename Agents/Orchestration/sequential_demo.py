import asyncio
import os

from agent_framework import AgentResponse
from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import SequentialBuilder
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

    print("\n=== SEQUENTIAL ORCHESTRATION DEMO ===\n")
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
    # Agent 1 - Policy Analyzer
    # ---------------------------------------------------------
    policy_agent = chat_client.as_agent(
        name="policy_agent",
        instructions=(
            "You are a company policy analyzer. "
            "For this demo, the company VPN policy says: "
            "'After three consecutive VPN authentication failures, "
            "the employee should contact the IT service desk.' "
            "Read the user's problem and state the relevant policy. "
            "Keep the answer short."
        ),
    )

    # ---------------------------------------------------------
    # Agent 2 - Response Writer
    # ---------------------------------------------------------
    response_agent = chat_client.as_agent(
        name="response_agent",
        instructions=(
            "You are an employee support response writer. "
            "You will receive the previous agent's response. "
            "Turn it into a short, clear response for the employee. "
            "Do not add new facts."
        ),
    )

    # ---------------------------------------------------------
    # Sequential workflow
    #
    # policy_agent
    #      ↓
    # response_agent
    # ---------------------------------------------------------
    workflow = SequentialBuilder(
        participants=[
            policy_agent,
            response_agent,
        ],
        chain_only_agent_responses=True,
        intermediate_output_from=[policy_agent],
    ).build()

    # ---------------------------------------------------------
    # User input
    # ---------------------------------------------------------
    question = "My VPN authentication failed three times. What should I do?"

    print("\nUSER:")
    print(question)

    print("\n--- WORKFLOW STARTED ---\n")

    # ---------------------------------------------------------
    # Run workflow
    # ---------------------------------------------------------
    async for event in workflow.run(question, stream=True):

        if event.type == "intermediate":
            update = event.data

            if getattr(update, "text", None):
                print("AGENT 1 - POLICY AGENT:")
                print(update.text)

        elif event.type == "output":
            update = event.data

            if getattr(update, "text", None):
                print("\nAGENT 2 - RESPONSE AGENT:")
                print(update.text)

    print("\n--- WORKFLOW COMPLETED ---")


if __name__ == "__main__":
    asyncio.run(main())