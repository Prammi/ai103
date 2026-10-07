import os
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
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

from analyze_incidents import analyze_incident


load_dotenv()


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL_NAME"]

INDEX_NAME = "corporate-incidents"


# ---------------------------------------------------------
# Azure authentication
# ---------------------------------------------------------

credential = DefaultAzureCredential()

token_provider = get_bearer_token_provider(
    credential,
    "https://ai.azure.com/.default",
)

openai_client = OpenAI(
    base_url=f"{OPENAI_ENDPOINT}/",
    api_key=token_provider,
)


# ---------------------------------------------------------
# Create Azure AI Search index
# ---------------------------------------------------------

def create_search_index():
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=credential,
    )

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
        ),

        SearchableField(
            name="employee",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="department",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="application_or_system",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="category",
            type=SearchFieldDataType.String,
        ),

        SearchField(
            name="symptoms",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.String
            ),
            searchable=True,
        ),

        SearchableField(
            name="error_details",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="severity",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="business_impact",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="evidence_from_attachment",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="priority",
            type=SearchFieldDataType.String,
        ),

        SearchableField(
            name="support_team",
            type=SearchFieldDataType.String,
        ),

        SearchField(
            name="search_terms",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.String
            ),
            searchable=True,
        ),

        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.Single
            ),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="incident-vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="incident-hnsw"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="incident-vector-profile",
                algorithm_configuration_name="incident-hnsw",
            )
        ],
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
    )

    # Delete the old index if it exists.
    try:
        index_client.delete_index(INDEX_NAME)
        print(f"Deleted existing index: {INDEX_NAME}")
    except Exception:
        pass

    index_client.create_index(index)

    print(f"Created Search index: {INDEX_NAME}")


# ---------------------------------------------------------
# Create embedding text
# ---------------------------------------------------------

def build_embedding_text(incident: dict) -> str:
    """
    Combine the most useful incident information into
    one piece of text for semantic/vector retrieval.
    """

    symptoms = " ".join(incident.get("symptoms", []))
    search_terms = " ".join(
        incident.get("enrichment", {}).get("search_terms", [])
    )

    return f"""
Application: {incident.get("application_or_system", "")}
Category: {incident.get("category", "")}
Symptoms: {symptoms}
Error: {incident.get("error_details", "")}
Business impact: {incident.get("business_impact", "")}
Search terms: {search_terms}
""".strip()


# ---------------------------------------------------------
# Generate embedding
# ---------------------------------------------------------

def generate_embedding(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


# ---------------------------------------------------------
# Convert GPT result into Search document
# ---------------------------------------------------------

def create_search_document(incident_id: str, incident: dict) -> dict:
    enrichment = incident.get("enrichment", {})

    embedding_text = build_embedding_text(incident)

    embedding = generate_embedding(embedding_text)

    return {
        "id": incident_id,
        "employee": incident.get("employee", ""),
        "department": incident.get("department", ""),
        "application_or_system": incident.get(
            "application_or_system",
            "",
        ),
        "category": incident.get("category", ""),
        "symptoms": incident.get("symptoms", []),
        "error_details": incident.get(
            "error_details",
            "",
        ),
        "severity": incident.get(
            "severity",
            "",
        ),
        "business_impact": incident.get(
            "business_impact",
            "",
        ),
        "evidence_from_attachment": incident.get(
            "evidence_from_attachment",
            "",
        ),
        "priority": enrichment.get(
            "priority",
            "",
        ),
        "support_team": enrichment.get(
            "support_team",
            "",
        ),
        "search_terms": enrichment.get(
            "search_terms",
            [],
        ),
        "content_vector": embedding,
    }


# ---------------------------------------------------------
# Analyze and upload incidents
# ---------------------------------------------------------

def upload_incidents():
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential,
    )

    email_files = sorted(
        Path("emails").glob("*.eml")
    )

    documents = []

    for number, email_path in enumerate(email_files, start=1):

        print()
        print("=" * 70)
        print(f"Processing: {email_path.name}")
        print("=" * 70)

        print("1. Extracting + enriching with GPT-5...")

        incident = analyze_incident(email_path)

        print("2. Generating embedding...")

        document = create_search_document(
            incident_id=f"INC-{number:03d}",
            incident=incident,
        )

        documents.append(document)

        print("3. Incident prepared for Search.")

    print()
    print("Uploading incidents to Azure AI Search...")

    result = search_client.upload_documents(
        documents=documents
    )

    for item in result:
        print(
            f"{item.key}: "
            f"{'Success' if item.succeeded else 'Failed'}"
        )

    print()
    print("All incidents uploaded.")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    create_search_index()
    upload_incidents()


if __name__ == "__main__":
    main()