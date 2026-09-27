import os
from pathlib import Path

from azure.identity import (
    DefaultAzureCredential,
    get_bearer_token_provider,
)
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from dotenv import load_dotenv
from openai import OpenAI
from openai import AuthenticationError, NotFoundError, PermissionDeniedError


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DATA_FOLDER = Path("data")

CHUNK_SIZE = 100
CHUNK_OVERLAP = 20


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

def load_configuration():
    load_dotenv()

    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    embedding_deployment_name = os.getenv(
        "EMBEDDING_DEPLOYMENT_NAME"
    )

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")

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
# Normalize Azure OpenAI / Foundry endpoint
# ---------------------------------------------------------

def build_openai_base_url(endpoint):
    endpoint = endpoint.strip().rstrip("/")

    # Do not use a Foundry project endpoint for embeddings.
    if "/api/projects/" in endpoint.lower():
        raise ValueError(
            "\nAZURE_OPENAI_ENDPOINT is a Foundry PROJECT endpoint.\n"
            "Embeddings must use the Azure OpenAI / Foundry resource "
            "OpenAI endpoint.\n\n"
            "Example:\n"
            "https://myresource.openai.azure.com\n"
            "or\n"
            "https://myresource.services.ai.azure.com\n"
        )

    # User may already have /openai/v1 in the .env value.
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
    base_url = build_openai_base_url(
        azure_openai_endpoint
    )

    print("\nEmbedding API base URL:")
    print(base_url)

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    client = OpenAI(
        base_url=base_url,
        api_key=token_provider,
    )

    return client


# ---------------------------------------------------------
# Test embedding deployment before processing documents
# ---------------------------------------------------------

def test_embedding_deployment(
    embedding_client,
    deployment_name,
):
    print("\nTesting embedding deployment...")
    print(f"Deployment name: {deployment_name}")

    try:
        response = embedding_client.embeddings.create(
            model=deployment_name,
            input="Test embedding request.",
        )

        vector = response.data[0].embedding

        print("Embedding deployment test: SUCCESS")
        print(
            f"Embedding dimensions: {len(vector)}"
        )

        return len(vector)

    except NotFoundError as exc:
        raise RuntimeError(
            "\nEmbedding deployment returned HTTP 404.\n\n"
            "The Python request format is correct, but Azure "
            "cannot find this deployment at this endpoint.\n\n"
            "Check these TWO values in Foundry:\n"
            "1. AZURE_OPENAI_ENDPOINT\n"
            "2. EMBEDDING_DEPLOYMENT_NAME\n\n"
            "The deployment must belong to the resource/account "
            "represented by AZURE_OPENAI_ENDPOINT.\n\n"
            f"Deployment currently used: {deployment_name}\n"
        ) from exc

    except AuthenticationError as exc:
        raise RuntimeError(
            "\nAzure returned HTTP 401.\n"
            "Authentication failed.\n"
            "Run 'az login' and verify your Azure account."
        ) from exc

    except PermissionDeniedError as exc:
        raise RuntimeError(
            "\nAzure returned HTTP 403.\n"
            "Authentication succeeded, but your identity "
            "does not have permission to use this AI resource."
        ) from exc


# ---------------------------------------------------------
# Chunk text
# ---------------------------------------------------------

def chunk_text(
    text,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP,
):
    if overlap >= chunk_size:
        raise ValueError(
            "CHUNK_OVERLAP must be smaller than CHUNK_SIZE"
        )

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):
        end = min(
            start + chunk_size,
            len(words),
        )

        chunk = " ".join(
            words[start:end]
        )

        chunks.append(chunk)

        if end == len(words):
            break

        start += chunk_size - overlap

    return chunks


# ---------------------------------------------------------
# Load .txt documents
# ---------------------------------------------------------

def load_documents():
    if not DATA_FOLDER.exists():
        raise FileNotFoundError(
            f"Data folder '{DATA_FOLDER}' does not exist."
        )

    documents = []

    for file_path in sorted(
        DATA_FOLDER.glob("*.txt")
    ):
        text = file_path.read_text(
            encoding="utf-8"
        )

        if not text.strip():
            print(
                f"Skipping empty file: "
                f"{file_path.name}"
            )
            continue

        documents.append(
            {
                "title": file_path.stem
                .replace("-", " ")
                .title(),
                "source": file_path.name,
                "content": text,
            }
        )

    if not documents:
        raise ValueError(
            "No valid .txt documents were found "
            "inside the data folder."
        )

    return documents


# ---------------------------------------------------------
# Generate embedding
# ---------------------------------------------------------

def generate_embedding(
    embedding_client,
    deployment_name,
    text,
):
    response = embedding_client.embeddings.create(
        model=deployment_name,
        input=text,
    )

    return response.data[0].embedding


# ---------------------------------------------------------
# Convert documents into searchable chunks
# ---------------------------------------------------------

def prepare_chunks(
    documents,
    embedding_client,
    embedding_deployment_name,
):
    indexed_chunks = []

    chunk_counter = 1

    for document in documents:
        chunks = chunk_text(
            document["content"]
        )

        print(
            f"\n{document['source']}: "
            f"{len(chunks)} chunk(s)"
        )

        for chunk_number, chunk in enumerate(
            chunks,
            start=1,
        ):
            vector = generate_embedding(
                embedding_client,
                embedding_deployment_name,
                chunk,
            )

            indexed_document = {
                "id": f"chunk-{chunk_counter}",
                "title": document["title"],
                "source": document["source"],
                "content": chunk,
                "contentVector": vector,
            }

            indexed_chunks.append(
                indexed_document
            )

            print(
                f"  Embedded chunk "
                f"{chunk_number} "
                f"({len(vector)} dimensions)"
            )

            chunk_counter += 1

    return indexed_chunks


# ---------------------------------------------------------
# Create Azure AI Search vector index
# ---------------------------------------------------------

def create_search_index(
    index_client,
    index_name,
    vector_dimensions,
):
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),

        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
        ),

        SimpleField(
            name="source",
            type=SearchFieldDataType.String,
            filterable=True,
        ),

        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
        ),

        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.Single
            ),
            searchable=True,
            vector_search_dimensions=vector_dimensions,
            vector_search_profile_name=(
                "support-vector-profile"
            ),
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="support-hnsw",
            )
        ],

        profiles=[
            VectorSearchProfile(
                name="support-vector-profile",
                algorithm_configuration_name=(
                    "support-hnsw"
                ),
            )
        ],
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
    )

    index_client.create_or_update_index(
        index
    )

    print(
        f"Search index '{index_name}' "
        f"created or updated successfully."
    )


# ---------------------------------------------------------
# Upload chunks to Azure AI Search
# ---------------------------------------------------------

def upload_chunks(
    search_endpoint,
    index_name,
    credential,
    chunks,
):
    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=index_name,
        credential=credential,
    )

    results = search_client.upload_documents(
        documents=chunks
    )

    failures = [
        result
        for result in results
        if not result.succeeded
    ]

    if failures:
        print(
            "\nSome documents failed to upload:"
        )

        for result in failures:
            print(
                f"ID: {result.key}"
            )
            print(
                f"Error: {result.error_message}"
            )

        raise RuntimeError(
            "One or more chunks failed to upload."
        )

    print(
        f"\nSuccessfully uploaded "
        f"{len(results)} chunk(s)."
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
        "RAG INGESTION PIPELINE"
    )
    print(
        "======================================"
    )

    print(
        "\nAzure AI endpoint:"
    )
    print(
        azure_openai_endpoint
    )

    print(
        "\nEmbedding deployment:"
    )
    print(
        embedding_deployment_name
    )

    print(
        "\nSearch endpoint:"
    )
    print(
        search_endpoint
    )

    print(
        "\nSearch index:"
    )
    print(
        search_index_name
    )

    print(
        "\nAuthenticating with Azure..."
    )

    credential = DefaultAzureCredential()

    # ---------------------------------------------
    # Create OpenAI embedding client
    # ---------------------------------------------

    embedding_client = create_embedding_client(
        azure_openai_endpoint,
        credential,
    )

    # ---------------------------------------------
    # IMPORTANT:
    # Test deployment BEFORE doing all ingestion
    # ---------------------------------------------

    vector_dimensions = (
        test_embedding_deployment(
            embedding_client,
            embedding_deployment_name,
        )
    )

    # ---------------------------------------------
    # Load company documents
    # ---------------------------------------------

    print(
        "\nLoading company documents..."
    )

    documents = load_documents()

    print(
        f"Loaded {len(documents)} document(s)."
    )

    # ---------------------------------------------
    # Chunk + embed
    # ---------------------------------------------

    print(
        "\nGenerating chunks and embeddings..."
    )

    chunks = prepare_chunks(
        documents,
        embedding_client,
        embedding_deployment_name,
    )

    if not chunks:
        raise RuntimeError(
            "No chunks were generated."
        )

    # Additional safety check
    actual_dimensions = len(
        chunks[0]["contentVector"]
    )

    if (
        actual_dimensions
        != vector_dimensions
    ):
        raise RuntimeError(
            "Embedding dimensions changed "
            "unexpectedly."
        )

    print(
        f"\nVector dimensions: "
        f"{vector_dimensions}"
    )

    # ---------------------------------------------
    # Create Search index
    # ---------------------------------------------

    print(
        "\nCreating Azure AI Search index..."
    )

    index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=credential,
    )

    create_search_index(
        index_client,
        search_index_name,
        vector_dimensions,
    )

    # ---------------------------------------------
    # Upload documents
    # ---------------------------------------------

    print(
        "\nUploading chunks..."
    )

    upload_chunks(
        search_endpoint,
        search_index_name,
        credential,
        chunks,
    )

    print(
        "\n======================================"
    )
    print(
        "RAG INGESTION COMPLETED SUCCESSFULLY"
    )
    print(
        "======================================"
    )


if __name__ == "__main__":
    main()