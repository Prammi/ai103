import json
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
MODEL = os.environ["MODEL_DEPLOYMENT_NAME"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL_NAME"]

INDEX_NAME = "corporate-incidents"


credential = DefaultAzureCredential()

token_provider = get_bearer_token_provider(
    credential,
    "https://ai.azure.com/.default",
)

openai_client = OpenAI(
    base_url=f"{OPENAI_ENDPOINT}/",
    api_key=token_provider,
)

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=credential,
)


def generate_embedding(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


def retrieve_incidents(query: str) -> list[dict]:
    """Retrieve similar incidents using hybrid search."""

    query_vector = generate_embedding(query)

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=3,
        fields="content_vector",
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        select=[
            "id",
            "employee",
            "department",
            "application_or_system",
            "category",
            "symptoms",
            "error_details",
            "priority",
            "business_impact",
            "support_team",
        ],
        top=3,
    )

    incidents = []

    for result in results:
        incidents.append(
            {
                "id": result["id"],
                "employee": result["employee"],
                "department": result["department"],
                "application_or_system": result[
                    "application_or_system"
                ],
                "category": result["category"],
                "symptoms": result["symptoms"],
                "error_details": result["error_details"],
                "priority": result["priority"],
                "business_impact": result["business_impact"],
                "support_team": result["support_team"],
            }
        )

    return incidents


def ground_incident(
    new_incident: str,
    retrieved_incidents: list[dict],
) -> dict:
    """Ask GPT-5 to analyze the incident using retrieved evidence."""

    evidence = json.dumps(
        retrieved_incidents,
        indent=2,
    )

    prompt = f"""
You are an enterprise IT incident analysis assistant.

Analyze the new incident using ONLY the retrieved historical
incidents as supporting evidence.

Do not invent facts.

NEW INCIDENT:
{new_incident}

RETRIEVED HISTORICAL INCIDENTS:
{evidence}

Return ONLY valid JSON:

{{
    "recommended_category": "",
    "recommended_priority": "",
    "recommended_support_team": "",
    "similar_incidents": [],
    "reasoning": ""
}}

The reasoning must explain how the retrieved incidents support
your recommendation.
"""

    response = openai_client.responses.create(
        model=MODEL,
        input=prompt,
    )

    return json.loads(response.output_text)


def main():
    new_incident = """
    During a customer presentation, Microsoft Teams keeps
    disconnecting and reconnecting. Other internet applications
    are working normally. The problem is disrupting the customer
    meeting.
    """

    print("=" * 70)
    print("NEW INCIDENT")
    print("=" * 70)
    print(new_incident)

    print("\nRetrieving similar incidents...")

    retrieved_incidents = retrieve_incidents(
        new_incident
    )

    print("\nRETRIEVED EVIDENCE")
    print("=" * 70)

    print(
        json.dumps(
            retrieved_incidents,
            indent=2,
        )
    )

    print("\nGrounding GPT-5 with retrieved evidence...")

    decision = ground_incident(
        new_incident,
        retrieved_incidents,
    )

    print("\nGROUNDED DECISION")
    print("=" * 70)

    print(
        json.dumps(
            decision,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()