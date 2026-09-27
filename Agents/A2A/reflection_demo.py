import asyncio
import os

from azure.identity import AzureCliCredential
from dotenv import load_dotenv

from agent_framework.foundry import FoundryChatClient


async def main():
    # ---------------------------------------------------------
    # 1. Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT is not set in .env")

    if not model_deployment_name:
        raise ValueError("MODEL_DEPLOYMENT_NAME is not set in .env")

    # ---------------------------------------------------------
    # 2. Create Foundry chat client
    # ---------------------------------------------------------
    chat_client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model_deployment_name,
        credential=AzureCliCredential(),
    )

    # ---------------------------------------------------------
    # 3. Create Writer Agent
    # ---------------------------------------------------------
    writer_agent = chat_client.as_agent(
        name="WriterAgent",
        instructions=(
            "You are a professional business email writer. "
            "Write clear and concise emails based on the user's request."
        ),
    )

    # ---------------------------------------------------------
    # 4. Create Reviewer Agent
    # ---------------------------------------------------------
    reviewer_agent = chat_client.as_agent(
        name="ReviewerAgent",
        instructions=(
            "You are a reviewer. "
            "Review the provided email draft. "
            "Identify important problems or missing information. "
            "Do not rewrite the email. "
            "Provide short and specific feedback."
        ),
    )

    # ---------------------------------------------------------
    # 5. User request
    # ---------------------------------------------------------
    user_request = (
        "Write an email to the customer explaining that "
        "the production deployment has been delayed."
    )

    print("\n========================================")
    print("USER REQUEST")
    print("========================================")
    print(user_request)

    # ---------------------------------------------------------
    # 6. Writer creates Draft V1
    # ---------------------------------------------------------
    draft_response = await writer_agent.run(user_request)

    draft_v1 = draft_response.text

    print("\n========================================")
    print("WRITER AGENT - DRAFT V1")
    print("========================================")
    print(draft_v1)

    # ---------------------------------------------------------
    # 7. Reviewer reviews Draft V1
    # ---------------------------------------------------------
    review_request = f"""
                        Review the following email draft.

                        Original user request:
                        {user_request}

                        Email draft:
                        {draft_v1}
                        """

    review_response = await reviewer_agent.run(review_request)

    feedback = review_response.text

    print("\n========================================")
    print("REVIEWER AGENT - FEEDBACK")
    print("========================================")
    print(feedback)

    # ---------------------------------------------------------
    # 8. Writer improves the draft using feedback
    # ---------------------------------------------------------
    improvement_request = f"""
Improve the email using the reviewer's feedback.

Original user request:
{user_request}

Original draft:
{draft_v1}

Reviewer feedback:
{feedback}

Return only the improved email.
"""

    improved_response = await writer_agent.run(improvement_request)

    final_draft = improved_response.text

    print("\n========================================")
    print("WRITER AGENT - IMPROVED DRAFT V2")
    print("========================================")
    print(final_draft)

    print("\n========================================")
    print("REFLECTION COMPLETE")
    print("========================================")


if __name__ == "__main__":
    asyncio.run(main()) 