import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
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


def search_similar_incidents(query: str):
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

    print("\nHYBRID SEARCH RESULTS")
    print("=" * 70)

    for result in results:
        print(f"ID              : {result['id']}")
        print(f"Employee        : {result['employee']}")
        print(f"Application     : {result['application_or_system']}")
        print(f"Category        : {result['category']}")
        print(f"Priority        : {result['priority']}")
        print(f"Support Team    : {result['support_team']}")
        print(f"Symptoms        : {result['symptoms']}")
        print(f"Score           : {result['@search.score']}")
        print("-" * 70)
def main():
    new_incident = """
    During a customer presentation, Microsoft Teams keeps disconnecting
    and reconnecting. Other internet applications are working normally.
    The problem is disrupting the customer meeting.
    """

    print("NEW INCIDENT:")
    print(new_incident)

    search_similar_incidents(new_incident)


if __name__ == "__main__":
    main()