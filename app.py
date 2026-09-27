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

    model_deployment_name = os.getenv(
        "MODEL_DEPLOYMENT_NAME"
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

    if not model_deployment_name:
        raise ValueError(
            "MODEL_DEPLOYMENT_NAME is missing from .env"
        )

    if not search_endpoint:
        raise ValueError(
            "AZURE_SEARCH_ENDPOINT is missing from .env"
        )

    return (
        azure_openai_endpoint,
        embedding_deployment_name,
        model_deployment_name,
        search_endpoint,
        search_index_name,
    )


# ---------------------------------------------------------
# Build OpenAI v1 endpoint
# ---------------------------------------------------------

def build_openai_base_url(endpoint):
    endpoint = endpoint.strip().rstrip("/")

    if "/api/projects/" in endpoint.lower():
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT must be the "
            "Azure OpenAI / Foundry resource endpoint, "
            "not the project endpoint."
        )

    if endpoint.endswith("/openai/v1"):
        return endpoint + "/"

    return endpoint + "/openai/v1/"


# ---------------------------------------------------------
# Create OpenAI client
# ---------------------------------------------------------

def create_openai_client(
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
# Create embedding for user question
# ---------------------------------------------------------

def generate_query_embedding(
    openai_client,
    embedding_deployment_name,
    question,
):
    response = openai_client.embeddings.create(
        model=embedding_deployment_name,
        input=question,
    )

    return response.data[0].embedding


# ---------------------------------------------------------
# Hybrid retrieval
# ---------------------------------------------------------

def retrieve_documents(
    search_client,
    question,
    query_vector,
    top=3,
):
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top,
        fields="contentVector",
        kind="vector",
    )

    results = search_client.search(
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
        top=top,
    )

    documents = []

    for result in results:
        documents.append(
            {
                "id": result["id"],
                "title": result["title"],
                "source": result["source"],
                "content": result["content"],
                "score": result.get(
                    "@search.score",
                    0,
                ),
            }
        )

    return documents


# ---------------------------------------------------------
# Build grounding context
# ---------------------------------------------------------

def build_context(documents):
    context_parts = []

    for position, document in enumerate(
        documents,
        start=1,
    ):
        context_part = (
            f"[Source {position}]\n"
            f"Title: {document['title']}\n"
            f"File: {document['source']}\n"
            f"Content:\n"
            f"{document['content']}\n"
        )

        context_parts.append(
            context_part
        )

    return "\n".join(
        context_parts
    )


# ---------------------------------------------------------
# Generate grounded answer
# ---------------------------------------------------------

def generate_grounded_answer(
    openai_client,
    model_deployment_name,
    question,
    context,
):
    instructions = """
You are a company IT support assistant.

Answer the user's question using ONLY the supplied company
documentation.

Rules:
1. Do not use outside knowledge.
2. If the documentation does not contain enough information,
   say: "I could not find this information in the company documentation."
3. Do not invent company policies.
4. Keep the answer concise.
5. Mention the source file used for the answer.
"""

    prompt = f"""
COMPANY DOCUMENTATION

{context}

USER QUESTION

{question}
"""

    response = openai_client.responses.create(
        model=model_deployment_name,
        instructions=instructions,
        input=prompt,
    )

    return response.output_text


# ---------------------------------------------------------
# Print retrieved documents
# ---------------------------------------------------------

def print_retrieval_results(documents):
    print("\n")
    print("=" * 70)
    print("RETRIEVED DOCUMENTS")
    print("=" * 70)

    for position, document in enumerate(
        documents,
        start=1,
    ):
        print(
            f"\n#{position}"
        )

        print(
            f"Title : {document['title']}"
        )

        print(
            f"Source: {document['source']}"
        )

        print(
            f"Score : {document['score']}"
        )

        print(
            f"Content: {document['content']}"
        )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    (
        azure_openai_endpoint,
        embedding_deployment_name,
        model_deployment_name,
        search_endpoint,
        search_index_name,
    ) = load_configuration()

    print(
        "======================================"
    )
    print(
        "COMPANY SUPPORT RAG APPLICATION"
    )
    print(
        "======================================"
    )

    credential = DefaultAzureCredential()

    # -----------------------------------------------------
    # Create clients
    # -----------------------------------------------------

    openai_client = create_openai_client(
        azure_openai_endpoint,
        credential,
    )

    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=search_index_name,
        credential=credential,
    )

    # -----------------------------------------------------
    # User question
    # -----------------------------------------------------

    question = input(
        "\nAsk a company support question: "
    ).strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    # -----------------------------------------------------
    # STEP 1: Embed the question
    # -----------------------------------------------------

    print(
        "\n1. Generating query embedding..."
    )

    query_vector = generate_query_embedding(
        openai_client,
        embedding_deployment_name,
        question,
    )

    print(
        f"   Vector dimensions: "
        f"{len(query_vector)}"
    )

    # -----------------------------------------------------
    # STEP 2: Retrieve documents
    # -----------------------------------------------------

    print(
        "\n2. Searching Azure AI Search..."
    )

    documents = retrieve_documents(
        search_client,
        question,
        query_vector,
        top=3,
    )

    if not documents:
        print(
            "\nNo relevant documents found."
        )
        return

    print_retrieval_results(
        documents
    )

    # -----------------------------------------------------
    # STEP 3: Build grounding context
    # -----------------------------------------------------

    print(
        "\n3. Building grounding context..."
    )

    context = build_context(
        documents
    )

    # -----------------------------------------------------
    # STEP 4: Send context + question to LLM
    # -----------------------------------------------------

    print(
        "\n4. Generating grounded answer..."
    )

    answer = generate_grounded_answer(
        openai_client,
        model_deployment_name,
        question,
        context,
    )

    # -----------------------------------------------------
    # Output
    # -----------------------------------------------------

    print("\n")
    print("=" * 70)
    print("GROUNDED ANSWER")
    print("=" * 70)

    print(
        f"\n{answer}"
    )


if __name__ == "__main__":
    main()