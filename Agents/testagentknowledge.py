import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


AGENT_NAME = "company-support-agent"


def main():
    print("\n=== TEST COMPANY SUPPORT AGENT + KNOWLEDGE ===\n")

    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    # ---------------------------------------------------------
    # Connect to Foundry project
    # ---------------------------------------------------------
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    # ---------------------------------------------------------
    # Get OpenAI client bound to our persisted agent
    # ---------------------------------------------------------
    openai_client = project_client.get_openai_client(
        agent_name=AGENT_NAME
    )

    # ---------------------------------------------------------
    # Create a conversation
    # ---------------------------------------------------------
    conversation = openai_client.conversations.create()

    print(f"Conversation ID: {conversation.id}")

    # ---------------------------------------------------------
    # Ask a question that requires company policy knowledge
    # ---------------------------------------------------------
    question = "My VPN authentication failed three times. What should I do?"

    print("\nUSER:")
    print(question)

    response = openai_client.responses.create(
        conversation=conversation.id,
        input=question,
    )

    print("\nAGENT:")
    print(response.output_text)

    # ---------------------------------------------------------
    # Show response items.
    # Useful for seeing MCP/tool activity returned by the API.
    # ---------------------------------------------------------
    print("\n=== RESPONSE OUTPUT ITEMS ===")

    for index, item in enumerate(response.output):
        print(f"\nItem {index + 1}")
        print(f"Type: {getattr(item, 'type', 'unknown')}")
        print(item)


if __name__ == "__main__":
    main()