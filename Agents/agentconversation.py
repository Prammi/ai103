import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


AGENT_NAME = "company-support-agent"


def load_configuration():
    """Load Foundry configuration."""
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    return project_endpoint


def create_project_client(project_endpoint):
    """Create the Microsoft Foundry project client."""
    credential = DefaultAzureCredential()

    return AIProjectClient(
        endpoint=project_endpoint,
        credential=credential,
    )


def main():
    print("\n=== COMPANY SUPPORT AGENT - CONVERSATION TEST ===\n")

    # ---------------------------------------------------------
    # 1. Load configuration
    # ---------------------------------------------------------
    project_endpoint = load_configuration()

    # ---------------------------------------------------------
    # 2. Connect to the Foundry project
    # ---------------------------------------------------------
    project_client = create_project_client(project_endpoint)

    # ---------------------------------------------------------
    # 3. Get an OpenAI client bound to our existing agent
    # ---------------------------------------------------------
    openai_client = project_client.get_openai_client(
        agent_name=AGENT_NAME
    )

    print(f"Connected to agent: {AGENT_NAME}")

    # ---------------------------------------------------------
    # 4. Create a conversation
    # ---------------------------------------------------------
    conversation = openai_client.conversations.create()

    print(f"Conversation ID: {conversation.id}")

    # ---------------------------------------------------------
    # 5. First message
    # ---------------------------------------------------------
    first_question = "My VPN authentication failed three times."

    print("\nUSER:")
    print(first_question)

    first_response = openai_client.responses.create(
        conversation=conversation.id,
        input=first_question,
    )

    print("\nAGENT:")
    print(first_response.output_text)

    # ---------------------------------------------------------
    # 6. Follow-up message
    #
    # Notice that we deliberately do NOT repeat:
    # "VPN authentication failed three times."
    #
    # The agent should understand "that" using the conversation.
    # ---------------------------------------------------------
    follow_up_question = "What should I do about that?"

    print("\nUSER:")
    print(follow_up_question)

    second_response = openai_client.responses.create(
        conversation=conversation.id,
        input=follow_up_question,
    )

    print("\nAGENT:")
    print(second_response.output_text)


if __name__ == "__main__":
    main()