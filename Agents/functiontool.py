import json
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    FunctionTool,
    PromptAgentDefinition,
    Tool,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai.types.responses import ResponseFunctionToolCall
from openai.types.responses.response_input_param import ResponseInputParam


AGENT_NAME = "support-ticket-agent"


# ---------------------------------------------------------
# REAL PYTHON FUNCTION
# ---------------------------------------------------------
def create_support_ticket(issue_type, description):
    """
    Simulates creating a ticket in an IT support system.
    """

    print("\n>>> PYTHON FUNCTION IS ACTUALLY RUNNING <<<")
    print(f"Issue type : {issue_type}")
    print(f"Description: {description}")

    # For learning purposes we return a fixed ticket number.
    # Later this could call ServiceNow, Jira, REST API, etc.
    return {
        "ticket_id": "INC-1001",
        "status": "Created",
        "issue_type": issue_type,
    }


def main():

    print("\n=== FUNCTION CALLING DEMO ===\n")

    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv(
        "MODEL_DEPLOYMENT_NAME",
        "gpt-5-mini",
    )

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    # ---------------------------------------------------------
    # Connect to Foundry
    # ---------------------------------------------------------
    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    openai_client = project.get_openai_client()

    # ---------------------------------------------------------
    # DEFINE THE FUNCTION TOOL
    #
    # This tells GPT:
    # - function name
    # - what it does
    # - what arguments it needs
    # ---------------------------------------------------------
    function_tool = FunctionTool(
        name="create_support_ticket",
        description=(
            "Create an IT support ticket when an employee "
            "asks for technical support."
        ),
        parameters={
            "type": "object",
            "properties": {
                "issue_type": {
                    "type": "string",
                    "description": (
                        "Type of IT issue, for example VPN, "
                        "Password, or Laptop."
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

    tools: list[Tool] = [function_tool]

    # ---------------------------------------------------------
    # CREATE AGENT
    # ---------------------------------------------------------
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions=(
                "You are an IT support assistant. "
                "When an employee explicitly asks you to create "
                "a support ticket, use the create_support_ticket tool."
            ),
            tools=tools,
        ),
    )

    print("Agent created.")
    print(f"Agent name   : {agent.name}")
    print(f"Agent version: {agent.version}")

    # ---------------------------------------------------------
    # CREATE CONVERSATION
    # ---------------------------------------------------------
    conversation = openai_client.conversations.create()

    question = (
        "My VPN authentication failed three times. "
        "Please create a support ticket for me."
    )

    print("\nUSER:")
    print(question)

    # ---------------------------------------------------------
    # SEND USER REQUEST TO AGENT
    # ---------------------------------------------------------
    response = openai_client.responses.create(
        input=question,
        conversation=conversation.id,
        extra_body={
            "agent_reference": {
                "name": agent.name,
                "type": "agent_reference",
            }
        },
    )

    # ---------------------------------------------------------
    # CHECK WHETHER AGENT REQUESTED OUR FUNCTION
    # ---------------------------------------------------------
    function_outputs: ResponseInputParam = []

    for item in response.output:

        print(f"\nResponse item type: {item.type}")

        if isinstance(item, ResponseFunctionToolCall):

            print("\n>>> AGENT REQUESTED FUNCTION <<<")
            print(f"Function : {item.name}")
            print(f"Arguments: {item.arguments}")

            if item.name == "create_support_ticket":

                arguments = json.loads(item.arguments)

                # ---------------------------------------------
                # OUR PYTHON CODE EXECUTES THE FUNCTION
                # ---------------------------------------------
                result = create_support_ticket(
                    issue_type=arguments["issue_type"],
                    description=arguments["description"],
                )

                # ---------------------------------------------
                # SEND FUNCTION RESULT BACK TO THE AGENT
                # ---------------------------------------------
                function_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

    # ---------------------------------------------------------
    # GET FINAL AGENT RESPONSE
    # ---------------------------------------------------------
    if function_outputs:

        final_response = openai_client.responses.create(
            input=function_outputs,
            conversation=conversation.id,
            extra_body={
                "agent_reference": {
                    "name": agent.name,
                    "type": "agent_reference",
                }
            },
        )

        print("\nAGENT FINAL RESPONSE:")
        print(final_response.output_text)

    else:
        print("\nAgent did not request the function.")


if __name__ == "__main__":
    main()