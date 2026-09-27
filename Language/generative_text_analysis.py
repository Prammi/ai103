import json
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main():
    # ---------------------------------------------------------
    # Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    if not model_deployment_name:
        raise ValueError("MODEL_DEPLOYMENT_NAME is not set in .env")

    # ---------------------------------------------------------
    # Connect to Microsoft Foundry
    # ---------------------------------------------------------
    credential = DefaultAzureCredential()

    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential,
    )

    # ---------------------------------------------------------
    # Get OpenAI client from the Foundry project
    # ---------------------------------------------------------
    openai_client = project_client.get_openai_client()

    # ---------------------------------------------------------
    # Customer support text
    # ---------------------------------------------------------
    customer_text = """
    I upgraded our factory monitoring application yesterday.
    Since the upgrade, the application crashes every few minutes.

    I have contacted support three times and nobody has fixed
    the problem. This is extremely frustrating because our
    production team depends on this application.

    Rolling back to the previous version temporarily fixes
    the problem.
    """

    # ---------------------------------------------------------
    # Ask the generative model to analyze the text
    # ---------------------------------------------------------
    prompt = f"""
    Analyze the following customer support message.

    Return ONLY valid JSON using this structure:

    {{
        "topic": "main topic of the message",
        "summary": "short summary of the problem",
        "tone": "customer tone",
        "issue": "specific technical issue",
        "business_impact": "business impact described by customer",
        "possible_resolution": "resolution mentioned in the message"
    }}

    Customer message:

    {customer_text}
    """

    response = openai_client.responses.create(
        model=model_deployment_name,
        input=prompt,
    )

    # ---------------------------------------------------------
    # Read model response
    # ---------------------------------------------------------
    output_text = response.output_text

    print("\n--- GENERATIVE TEXT ANALYSIS ---")
    print(output_text)

    # ---------------------------------------------------------
    # Parse JSON so we prove that the output can be consumed
    # by an application
    # ---------------------------------------------------------
    try:
        analysis = json.loads(output_text)

        print("\n--- APPLICATION READING THE JSON ---")
        print(f"Topic: {analysis.get('topic')}")
        print(f"Summary: {analysis.get('summary')}")
        print(f"Tone: {analysis.get('tone')}")
        print(f"Issue: {analysis.get('issue')}")
        print(f"Business Impact: {analysis.get('business_impact')}")
        print(
            f"Possible Resolution: "
            f"{analysis.get('possible_resolution')}"
        )

    except json.JSONDecodeError:
        print("\nThe model response was not valid JSON.")


if __name__ == "__main__":
    main()