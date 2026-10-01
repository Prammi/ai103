import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main():
    # Clear console
    os.system("cls" if os.name == "nt" else "clear")

    # Load variables from .env
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    # ---------------------------------------------------------
    # Existing Foundry agent
    # ---------------------------------------------------------
    agent_name = "ai103-language-agent"

    # ---------------------------------------------------------
    # Connect to our Foundry project
    # ---------------------------------------------------------
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    # ---------------------------------------------------------
    # Get an OpenAI client connected to our EXISTING agent
    # ---------------------------------------------------------
    openai_client = project_client.get_openai_client(
        agent_name=agent_name
    )

    # ---------------------------------------------------------
    # Ask the agent to perform two text-analysis tasks
    # ---------------------------------------------------------
    user_prompt = """
    Use the available Azure Language tools to:

    1. Identify all named entities in the text.
    2. Analyze the sentiment of the text.

    Text:
    Microsoft opened a new research center in Hyderabad.
    I am extremely happy about this announcement and think
    it is fantastic news.
    """

    # ---------------------------------------------------------
    # Invoke the existing Foundry agent
    # ---------------------------------------------------------
    response = openai_client.responses.create(
        input=user_prompt
    )

    # ---------------------------------------------------------
    # Print final agent response
    # ---------------------------------------------------------
    print(response.output_text)


if __name__ == "__main__":
    main()