import asyncio
import os

from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def select_next_speaker(state: GroupChatState) -> str:
    participant_names = list(state.participants.keys())

    selected_agent = participant_names[
        state.current_round % len(participant_names)
    ]

    print(
        f"\n\nROUND {state.current_round} -> "
        f"{selected_agent}\n"
    )

    return selected_agent

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
        raise ValueError(
            "PROJECT_ENDPOINT is not set in .env"
        )

    print("\n=== GROUP CHAT ORCHESTRATION DEMO ===\n")
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
    # IT Agent
    # ---------------------------------------------------------
    it_agent = chat_client.as_agent(
        name="it_agent",
        instructions=(
            "You are the IT specialist in a group discussion. "
            "Read the existing conversation before responding. "
            "Give one short IT-related recommendation. "
            "Do not repeat points already made."
        ),
    )

    # ---------------------------------------------------------
    # Security Agent
    # ---------------------------------------------------------
    security_agent = chat_client.as_agent(
        name="security_agent",
        instructions=(
            "You are the security specialist in a group discussion. "
            "Read the existing conversation before responding. "
            "Give one short security-related recommendation. "
            "Build on what the other agent has already said. "
            "Do not repeat points already made."
        ),
    )

    # ---------------------------------------------------------
    # Group Chat
    #
    # IT Agent <---- shared conversation ----> Security Agent
    #
    # We stop after four messages.
    # ---------------------------------------------------------
    workflow = GroupChatBuilder(
        participants=[
            it_agent,
            security_agent,
        ],
        selection_func=select_next_speaker,
        termination_condition=lambda conversation: len(conversation) >= 4,
        intermediate_output_from=[
            it_agent,
            security_agent,
        ],
    ).build()

    # ---------------------------------------------------------
    # User question
    # ---------------------------------------------------------
    question = (
        "An employee lost their company laptop while travelling. "
        "What should the company do?"
    )

    print("\nUSER:")
    print(question)

    print("\n--- GROUP CHAT STARTED ---\n")

    # ---------------------------------------------------------
    # Run workflow
    # ---------------------------------------------------------
    async for event in workflow.run(
        question,
        stream=True,
    ):
        if event.type == "intermediate":
            data = event.data

            if getattr(data, "text", None):
                print(
                    data.text,
                    end="",
                    flush=True,
                )

        elif event.type == "output":
            data = event.data

            if getattr(data, "text", None):
                print(
                    "\n\nFINAL:\n",
                    data.text,
                )

    print("\n\n--- GROUP CHAT COMPLETED ---")


if __name__ == "__main__":
    asyncio.run(main())