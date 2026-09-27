import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def load_configuration():
    """Load configuration from the .env file."""
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5-mini")

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    return project_endpoint, model_deployment


def create_project_client(project_endpoint):
    """Create the Microsoft Foundry project client."""
    credential = DefaultAzureCredential()

    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential,
    )

    return project_client


def create_agent(project_client, model_deployment):
    """Create a versioned Company Support Agent."""

    agent = project_client.agents.create_version(
        agent_name="company-support-agent",
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions=(
                "You are a company support assistant. "
                "Help employees with company support questions. "
                "Be concise and professional. "
                "If you do not know something, say that you do not know."
            ),
        ),
    )

    return agent


def main():
    print("\n=== COMPANY SUPPORT AGENT ===\n")

    project_endpoint, model_deployment = load_configuration()

    print(f"Model deployment: {model_deployment}")

    project_client = create_project_client(project_endpoint)

    print("\nCreating agent...")

    agent = create_agent(
        project_client=project_client,
        model_deployment=model_deployment,
    )

    print("\nAgent created successfully.")
    print(f"Agent name    : {agent.name}")
    print(f"Agent version : {agent.version}")
    print(f"Agent ID      : {agent.id}")


if __name__ == "__main__":
    main()