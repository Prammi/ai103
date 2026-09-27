import os

from azure.identity import (
    DefaultAzureCredential,
    get_bearer_token_provider,
)
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------
# Load configuration
# ---------------------------------------------------------

def load_configuration():
    load_dotenv()

    azure_openai_endpoint = os.getenv(
        "AZURE_OPENAI_ENDPOINT"
    )

    embedding_deployment_name = os.getenv(
        "EMBEDDING_DEPLOYMENT_NAME"
    )

    search_endpoint = os.getenv(
        "AZURE_SEARCH_ENDPOINT"
    )

    search_index_name = os.getenv(
        "AZURE_SEARCH_INDEX_NAME",
        "support-index",
    )

    if not azure_openai_endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT is missing from .env"
        )

    if not embedding_deployment_name:
        raise ValueError(
            "EMBEDDING_DEPLOYMENT_NAME is missing from .env"
        )

    if not search_endpoint:
        raise ValueError(
            "AZURE_SEARCH_ENDPOINT is missing from .env"
        )

    return (
        azure_openai_endpoint,
        embedding_deployment_name,
        search_endpoint,
        search_index_name,
    )


# ---------------------------------------------------------
# Normalize OpenAI endpoint
# ---------------------------------------------------------

def build_openai_base_url(endpoint):
    endpoint = endpoint.strip().rstrip("/")

    if "/api/projects/" in endpoint.lower():
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT must be the "
            "Azure OpenAI / Foundry resource endpoint, "
            "not the Foundry project endpoint."
        )

    if endpoint.endswith("/openai/v1"):
        return endpoint + "/"

    return endpoint + "/openai/v1/"


# ---------------------------------------------------------
# Create embedding client
# ---------------------------------------------------------

def create_embedding_client(
    azure_openai_endpoint,
    credential,
):
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    base_url = build_openai_base_url(
        azure_openai_endpoint
    )

    return OpenAI(
        base_url=base_url,
        api_key=token_provider,
    )


# ---------------------------------------------------------
# Create query embedding
# ---------------------------------------------------------

def generate_query_embedding(
    embedding_client,
    deployment_name,
    question,
):
    response = embedding_client.embeddings.create(
        model=deployment_name,
        input=question,
    )

    return response.data[0].embedding


# ---------------------------------------------------------
# Print results
# ---------------------------------------------------------

def print_results(
    heading,
    results,
):
    print("\n")
    print("=" * 70)
    print(heading)
    print("=" * 70)

    found = False

    for position, result in enumerate(
        results,
        start=1,
    ):
        found = True

        score = result.get(
            "@search.score",
            0,
        )

        print(
            f"\nResult #{position}"
        )

        print(
            f"Score : {score}"
        )

        print(
            f"Title : {result.get('title')}"
        )

        print(
            f"Source: {result.get('source')}"
        )

        print(
            "Content:"
        )

        print(
            result.get(
                "content",
                "",
            )
        )

    if not found:
        print(
            "\nNo matching documents found."
        )


# ---------------------------------------------------------
# Keyword search
# ---------------------------------------------------------

def keyword_search(
    search_client,
    question,
):
    return search_client.search(
        search_text=question,
        select=[
            "id",
            "title",
            "source",
            "content",
        ],
        top=3,
    )


# ---------------------------------------------------------
# Vector search
# ---------------------------------------------------------

def vector_search(
    search_client,
    query_vector,
):
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=3,
        fields="contentVector",
        kind="vector",
    )

    return search_client.search(
        search_text=None,
        vector_queries=[
            vector_query
        ],
        select=[
            "id",
            "title",
            "source",
            "content",
        ],
        top=3,
    )


# ---------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------

def hybrid_search(
    search_client,
    question,
    query_vector,
):
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=3,
        fields="contentVector",
        kind="vector",
    )

    return search_client.search(
        search_text=question,
        vector_queries=[
            vector_query
        ],
        select=[
            "id",
            "title",
            "source",
            "content",
        ],
        top=3,
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    (
        azure_openai_endpoint,
        embedding_deployment_name,
        search_endpoint,
        search_index_name,
    ) = load_configuration()

    print(
        "======================================"
    )
    print(
        "RAG RETRIEVAL TEST"
    )
    print(
        "======================================"
    )

    credential = DefaultAzureCredential()

    # -----------------------------------------------------
    # Create embedding client
    # -----------------------------------------------------

    embedding_client = create_embedding_client(
        azure_openai_endpoint,
        credential,
    )

    # -----------------------------------------------------
    # Create Search client
    # -----------------------------------------------------

    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=search_index_name,
        credential=credential,
    )

    # -----------------------------------------------------
    # Ask question
    # -----------------------------------------------------

    question = input(
        "\nEnter your question: "
    ).strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    print(
        "\nGenerating query embedding..."
    )

    query_vector = generate_query_embedding(
        embedding_client,
        embedding_deployment_name,
        question,
    )

    print(
        f"Query embedding dimensions: "
        f"{len(query_vector)}"
    )

    # -----------------------------------------------------
    # 1. Keyword
    # -----------------------------------------------------

    keyword_results = keyword_search(
        search_client,
        question,
    )

    print_results(
        "1. KEYWORD SEARCH",
        keyword_results,
    )

    # -----------------------------------------------------
    # 2. Vector
    # -----------------------------------------------------

    vector_results = vector_search(
        search_client,
        query_vector,
    )

    print_results(
        "2. VECTOR SEARCH",
        vector_results,
    )

    # -----------------------------------------------------
    # 3. Hybrid
    # -----------------------------------------------------

    hybrid_results = hybrid_search(
        search_client,
        question,
        query_vector,
    )

    print_results(
        "3. HYBRID SEARCH",
        hybrid_results,
    )


if __name__ == "__main__":
    main()