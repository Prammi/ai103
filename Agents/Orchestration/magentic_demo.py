import asyncio
import os

from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import MagenticBuilder
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


async def main():
    # ---------------------------------------------------------
    # Load configuration
    # ---------------------------------------------------------
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv(
        "MODEL_DEPLOYMENT_NAME",
        "gpt-5-mini",
    )

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    print("\n=== MAGENTIC ORCHESTRATION DEMO ===\n")
    print(f"Model: {model_deployment}")

    # ---------------------------------------------------------
    # Foundry Chat Client
    # ---------------------------------------------------------
    chat_client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model_deployment,
        credential=DefaultAzureCredential(),
    )

    # ---------------------------------------------------------
    # Agent 1 - Ingredient Specialist
    # ---------------------------------------------------------
    ingredient_agent = chat_client.as_agent(
        name="ingredient_agent",
        description=(
            "Determines the ingredients and quantities "
            "required for making tea."
        ),
        instructions=(
            "You are an ingredient specialist. "
            "When asked about preparing tea, determine "
            "the ingredients and quantities required. "
            "Keep your response short."
        ),
    )

    # ---------------------------------------------------------
    # Agent 2 - Preparation Specialist
    # ---------------------------------------------------------
    preparation_agent = chat_client.as_agent(
        name="preparation_agent",
        description=(
            "Determines the steps required to prepare tea."
        ),
        instructions=(
            "You are a tea preparation specialist. "
            "Determine the preparation steps required. "
            "Use information already available from the team. "
            "Keep your response short."
        ),
    )

    # ---------------------------------------------------------
    # Agent 3 - Quality Reviewer
    # ---------------------------------------------------------
    quality_agent = chat_client.as_agent(
        name="quality_agent",
        description=(
            "Reviews a tea preparation plan and identifies "
            "anything important that is missing."
        ),
        instructions=(
            "You are a quality reviewer. "
            "Review the team's tea preparation plan. "
            "Identify anything important that is missing. "
            "Do not repeat information unnecessarily."
        ),
    )

    # ---------------------------------------------------------
    # Magentic Manager
    # ---------------------------------------------------------
    manager_agent = chat_client.as_agent(
        name="magentic_manager",
        description=(
            "Coordinates specialists to complete the user's goal."
        ),
        instructions=(
            "You are the manager. "
            "Analyze the user's goal, decide which specialist "
            "should work next, track progress, and make sure "
            "the final goal is completed."
        ),
    )

    # ---------------------------------------------------------
    # Build Magentic Workflow
    #
    # IMPORTANT:
    # We are NOT specifying:
    #
    # ingredient -> preparation -> quality
    #
    # The MANAGER decides whom to invoke.
    # ---------------------------------------------------------
    workflow = MagenticBuilder(
        participants=[
            ingredient_agent,
            preparation_agent,
            quality_agent,
        ],
        manager_agent=manager_agent,
        intermediate_output_from=[
            ingredient_agent,
            preparation_agent,
            quality_agent,
        ],
        max_round_count=6,
        max_stall_count=2,
        max_reset_count=1,
    ).build()

    # ---------------------------------------------------------
    # Goal
    # ---------------------------------------------------------
    goal = (
        "Prepare a simple plan for making tea for four people. "
        "Make sure the ingredients and preparation steps "
        "are complete."
    )

    print("\nGOAL:")
    print(goal)

    print("\n--- MAGENTIC WORKFLOW STARTED ---\n")

        # ---------------------------------------------------------
    # Run workflow - clean readable output
    # ---------------------------------------------------------
    async for event in workflow.run(goal, stream=True):

        # Specialist agent completed a response
        if event.type == "intermediate":
            data = event.data

            agent_name = getattr(data, "author_name", None)
            text = getattr(data, "text", None)

            if text:
                print("\n" + "=" * 60)

                if agent_name:
                    print(f"AGENT: {agent_name}")
                else:
                    print("SPECIALIST AGENT")

                print("=" * 60)
                print(text.strip())

        # Final Magentic result
        elif event.type == "output":
            data = event.data
            text = getattr(data, "text", None)

            if text:
                print("\n" + "=" * 60)
                print("FINAL RESULT")
                print("=" * 60)
                print(text.strip())

    print("\n" + "=" * 60)
    print("MAGENTIC WORKFLOW COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())