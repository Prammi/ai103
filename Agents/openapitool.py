import os
import jsonref
from typing import Any, cast

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    OpenApiTool,
    OpenApiFunctionDefinition,
    OpenApiAnonymousAuthDetails,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


AGENT_NAME = "weather-openapi-agent"


def load_configuration():
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv(
        "MODEL_DEPLOYMENT_NAME",
        "gpt-5-mini",
    )

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    return project_endpoint, model_deployment


def load_openapi_spec():
    current_directory = os.path.dirname(
        os.path.abspath(__file__)
    )

    spec_path = os.path.join(
        current_directory,
        "weather_openapi.json",
    )

    with open(spec_path, "r", encoding="utf-8") as file:
        specification = cast(
            dict[str, Any],
            jsonref.loads(file.read()),
        )

    return specification


def create_agent(
    project,
    model_deployment,
    openapi_specification,
):
    weather_tool = OpenApiTool(
        openapi=OpenApiFunctionDefinition(
            name="weather_api",
            spec=openapi_specification,
            description=(
                "Get current weather information "
                "for a requested location."
            ),
            auth=OpenApiAnonymousAuthDetails(),
        )
    )

    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions=(
                "You are a weather assistant. "
                "When the user asks about current weather, "
                "use the weather API tool."
            ),
            tools=[weather_tool],
        ),
    )

    return agent


def main():
    print("\n=== OPENAPI TOOL DEMO ===\n")

    project_endpoint, model_deployment = load_configuration()

    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    openapi_specification = load_openapi_spec()

    print("OpenAPI specification loaded.")

    agent = create_agent(
        project=project,
        model_deployment=model_deployment,
        openapi_specification=openapi_specification,
    )

    print("\nAgent created.")
    print(f"Agent name    : {agent.name}")
    print(f"Agent version : {agent.version}")

    # Client bound to this agent
    openai_client = project.get_openai_client(
        agent_name=AGENT_NAME
    )

    conversation = openai_client.conversations.create()

    question = "What is the current weather in Hyderabad?"

    print("\nUSER:")
    print(question)

    response = openai_client.responses.create(
        conversation=conversation.id,
        input=question,
    )

    print("\n=== RESPONSE ITEMS ===")

    for item in response.output:
        print(f"\nType: {item.type}")

        if item.type == "openapi_call":
            print("OpenAPI tool was called.")
            print(item)

    print("\n=== FINAL ANSWER ===")
    print(response.output_text)


if __name__ == "__main__":
    main()