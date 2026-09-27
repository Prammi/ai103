import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


AGENT_NAME = "company-support-agent"


def load_configuration():
    """Load configuration from .env."""

    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    search_service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    knowledge_base_name = os.getenv("KNOWLEDGE_BASE_NAME")
    connection_name = os.getenv("KB_CONNECTION_NAME")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5-mini")

    required_values = {
        "PROJECT_ENDPOINT": project_endpoint,
        "SEARCH_SERVICE_ENDPOINT": search_service_endpoint,
        "KNOWLEDGE_BASE_NAME": knowledge_base_name,
        "KB_CONNECTION_NAME": connection_name,
    }

    for name, value in required_values.items():
        if not value:
            raise ValueError(f"{name} is not set in .env")

    return (
        project_endpoint,
        search_service_endpoint.rstrip("/"),
        knowledge_base_name,
        connection_name,
        model_deployment,
    )


def create_project_client(project_endpoint):
    """Create the Foundry project client."""

    credential = DefaultAzureCredential()

    return AIProjectClient(
        endpoint=project_endpoint,
        credential=credential,
    )


def create_agent_with_knowledge(
    project_client,
    search_service_endpoint,
    knowledge_base_name,
    connection_name,
    model_deployment,
):
    """Create a new version of the agent with Knowledge Base access."""

    mcp_endpoint = (
        f"{search_service_endpoint}"
        f"/knowledgebases/{knowledge_base_name}/mcp"
        f"?api-version=2026-08-01-preview"
    )

    # ---------------------------------------------------------
    # Knowledge Base MCP tool
    # ---------------------------------------------------------
    mcp_kb_tool = MCPTool(
        server_label="knowledge-base",
        server_url=mcp_endpoint,
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=connection_name,
    )

    # ---------------------------------------------------------
    # Agent instructions
    # ---------------------------------------------------------
    instructions = """
You are a company support assistant.

You must use the company knowledge base to answer company policy questions.

Do not answer company policy questions using your own general knowledge.

If the knowledge base does not contain the answer, say:
"I don't know based on the available company documentation."

When information comes from the knowledge base, preserve the source
citations returned by the knowledge base.

Keep answers concise and professional.
"""

    # ---------------------------------------------------------
    # Create NEW VERSION of existing agent
    # ---------------------------------------------------------
    agent = project_client.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions=instructions,
            tools=[mcp_kb_tool],
        ),
    )

    return agent


def main():
    print("\n=== COMPANY SUPPORT AGENT + KNOWLEDGE BASE ===\n")

    (
        project_endpoint,
        search_service_endpoint,
        knowledge_base_name,
        connection_name,
        model_deployment,
    ) = load_configuration()

    project_client = create_project_client(project_endpoint)

    print(f"Agent name       : {AGENT_NAME}")
    print(f"Model            : {model_deployment}")
    print(f"Knowledge Base   : {knowledge_base_name}")
    print(f"Connection       : {connection_name}")

    print("\nCreating new agent version with Knowledge Base access...")

    agent = create_agent_with_knowledge(
        project_client=project_client,
        search_service_endpoint=search_service_endpoint,
        knowledge_base_name=knowledge_base_name,
        connection_name=connection_name,
        model_deployment=model_deployment,
    )

    print("\nAgent created successfully.")
    print(f"Agent name    : {agent.name}")
    print(f"Agent version : {agent.version}")
    print(f"Agent ID      : {agent.id}")


if __name__ == "__main__":
    main()