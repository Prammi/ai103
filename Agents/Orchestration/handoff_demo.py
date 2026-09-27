import asyncio
import os

from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import HandoffBuilder
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

    print("\n=== HANDOFF ORCHESTRATION DEMO ===\n")
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
    # Triage Agent
    # ---------------------------------------------------------
    triage_agent = chat_client.as_agent(
        name="triage_agent",
        instructions=(
            "You are the first-line company support agent. "
            "Determine whether the employee's request is related "
            "to IT or HR. "
            "For IT problems, hand off to the IT agent. "
            "For HR problems, hand off to the HR agent. "
            "Do not try to solve specialist problems yourself."
        ),
        require_per_service_call_history_persistence=True,
        
    )

    # ---------------------------------------------------------
    # IT Agent
    # ---------------------------------------------------------
    it_agent = chat_client.as_agent(
        name="it_agent",
        instructions=(
            "You are an IT support specialist. "
            "Handle VPN, laptop, password, software, and other "
            "technical support problems. "
            "Keep your response short."
        ),
        require_per_service_call_history_persistence=True,
    )

    # ---------------------------------------------------------
    # HR Agent
    # ---------------------------------------------------------
    hr_agent = chat_client.as_agent(
        name="hr_agent",
        instructions=(
            "You are an HR support specialist. "
            "Handle leave, benefits, relocation, payroll, "
            "and other HR-related questions. "
            "Keep your response short."
        ),
        require_per_service_call_history_persistence=True,
    )

    # ---------------------------------------------------------
    # Build handoff workflow
    #
    #                  ┌──> IT Agent
    # Triage Agent ────┤
    #                  └──> HR Agent
    # ---------------------------------------------------------
    workflow = (
        HandoffBuilder(
            participants=[
                triage_agent,
                it_agent,
                hr_agent,
            ]
        )
        .with_start_agent(triage_agent)
        .add_handoff(
            triage_agent,
            [
                it_agent,
                hr_agent,
            ],
        )
        .build()
    )

    # ---------------------------------------------------------
    # Test question
    # Change this to an HR question for the second test.
    # ---------------------------------------------------------
    question = "My VPN authentication keeps failing. Can you help me?"

    print("\nUSER:")
    print(question)

    print("\n--- WORKFLOW STARTED ---\n")

    async for event in workflow.run(question, stream=True):

        # Show when a handoff occurs
        if event.type == "handoff_sent":
            print("\n>>> HANDOFF OCCURRED <<<\n")

        # Print model output continuously
        elif event.type == "output":
            data = event.data

            if getattr(data, "text", None):
                print(data.text, end="", flush=True)

    print("\n\n--- WORKFLOW COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(main())