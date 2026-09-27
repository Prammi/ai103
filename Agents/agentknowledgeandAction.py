import json
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    FunctionTool,
    MCPTool,
    PromptAgentDefinition,
    Tool,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai.types.responses import ResponseFunctionToolCall
from openai.types.responses.response_input_param import ResponseInputParam


AGENT_NAME = "company-support-combined-agent"


# ---------------------------------------------------------
# ACTION TOOL
# ---------------------------------------------------------
def create_support_ticket(issue_type, description):
    """Simulate creating an IT support ticket."""

    print("\n>>> CREATE SUPPORT TICKET FUNCTION EXECUTED <<<")
    print(f"Issue type : {issue_type}")
    print(f"Description: {description}")

    return {
        "ticket_id": "INC-1001",
        "status": "Created",
        "issue_type": issue_type,
    }


def load_configuration():
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv(
        "MODEL_DEPLOYMENT_NAME",
        "gpt-5-mini",
    )

    search_service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    knowledge_base_name = os.getenv("KNOWLEDGE_BASE_NAME")
    connection_name = os.getenv("KB_CONNECTION_NAME")

    required = {
        "PROJECT_ENDPOINT": project_endpoint,
        "SEARCH_SERVICE_ENDPOINT": search_service_endpoint,
        "KNOWLEDGE_BASE_NAME": knowledge_base_name,
        "KB_CONNECTION_NAME": connection_name,
    }

    for name, value in required.items():
        if not value:
            raise ValueError(f"{name} is not set in .env")

    return (
        project_endpoint,
        model_deployment,
        search_service_endpoint.rstrip("/"),
        knowledge_base_name,
        connection_name,
    )


def create_agent(
    project,
    model_deployment,
    search_service_endpoint,
    knowledge_base_name,
    connection_name,
):

    # ---------------------------------------------------------
    # TOOL 1: KNOWLEDGE BASE
    # ---------------------------------------------------------
    mcp_endpoint = (
        f"{search_service_endpoint}"
        f"/knowledgebases/{knowledge_base_name}/mcp"
        f"?api-version=2026-08-01-preview"
    )

    knowledge_tool = MCPTool(
        server_label="knowledge-base",
        server_url=mcp_endpoint,
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=connection_name,
    )

    # ---------------------------------------------------------
    # TOOL 2: CREATE SUPPORT TICKET
    # ---------------------------------------------------------
    ticket_tool = FunctionTool(
        name="create_support_ticket",
        description=(
            "Create an IT support ticket when the employee "
            "explicitly asks for a support ticket."
        ),
        parameters={
            "type": "object",
            "properties": {
                "issue_type": {
                    "type": "string",
                    "description": (
                        "Type of issue such as VPN, Password, or Laptop."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Description of the employee's problem."
                    ),
                },
            },
            "required": [
                "issue_type",
                "description",
            ],
            "additionalProperties": False,
        },
        strict=True,
    )

    tools: list[Tool] = [
        knowledge_tool,
        ticket_tool,
    ]

    # ---------------------------------------------------------
    # CREATE AGENT
    # ---------------------------------------------------------
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions=(
                "You are a company IT support assistant. "
                "Use the company knowledge base for company policy "
                "questions. Do not invent company policies. "
                "If the employee explicitly asks you to create a "
                "support ticket, use the create_support_ticket tool. "
                "When appropriate, first retrieve the relevant company "
                "policy and then perform the requested action."
            ),
            tools=tools,
        ),
    )

    return agent


def main():
    print("\n=== COMPANY SUPPORT: KNOWLEDGE + ACTION ===\n")

    (
        project_endpoint,
        model_deployment,
        search_service_endpoint,
        knowledge_base_name,
        connection_name,
    ) = load_configuration()

    # ---------------------------------------------------------
    # PROJECT CLIENT
    # ---------------------------------------------------------
    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    # ---------------------------------------------------------
    # CREATE COMBINED AGENT
    # ---------------------------------------------------------
    agent = create_agent(
        project=project,
        model_deployment=model_deployment,
        search_service_endpoint=search_service_endpoint,
        knowledge_base_name=knowledge_base_name,
        connection_name=connection_name,
    )

    print(f"Agent name    : {agent.name}")
    print(f"Agent version : {agent.version}")

    # ---------------------------------------------------------
    # CLIENT BOUND TO THIS AGENT
    # ---------------------------------------------------------
    openai_client = project.get_openai_client(
        agent_name=AGENT_NAME
    )

    conversation = openai_client.conversations.create()

    question = (
        "My VPN authentication failed three times. "
        "What should I do? "
        "If company policy says I should contact IT, "
        "create a support ticket for me."
    )

    print("\nUSER:")
    print(question)

    # ---------------------------------------------------------
    # FIRST AGENT RESPONSE
    # ---------------------------------------------------------
    response = openai_client.responses.create(
        conversation=conversation.id,
        input=question,
    )

    print("\n=== FIRST RESPONSE ITEMS ===")

    function_outputs: ResponseInputParam = []

    for item in response.output:

        print(f"\nType: {item.type}")

        # MCP calls are executed by Foundry.
        if item.type == "mcp_call":
            print("Knowledge Base MCP tool was called.")
            print(f"Tool: {item.name}")

        # Function calls must be executed by OUR application.
        if isinstance(item, ResponseFunctionToolCall):

            print("\n>>> AGENT REQUESTED ACTION <<<")
            print(f"Function : {item.name}")
            print(f"Arguments: {item.arguments}")

            if item.name == "create_support_ticket":

                arguments = json.loads(item.arguments)

                result = create_support_ticket(
                    issue_type=arguments["issue_type"],
                    description=arguments["description"],
                )

                function_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

    # ---------------------------------------------------------
    # RETURN FUNCTION RESULT TO AGENT
    # ---------------------------------------------------------
    if function_outputs:

        final_response = openai_client.responses.create(
            conversation=conversation.id,
            input=function_outputs,
        )

        print("\n=== FINAL AGENT RESPONSE ===")
        print(final_response.output_text)

    else:
        print("\n=== AGENT RESPONSE ===")
        print(response.output_text)


if __name__ == "__main__":
    main()