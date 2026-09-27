import os

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
    SearchIndexFieldReference,
    KnowledgeBase,
    KnowledgeSourceReference,
)
from azure.search.documents.knowledgebases import (
    KnowledgeBaseRetrievalClient,
)

from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalSemanticIntent,
    SearchIndexKnowledgeSourceParams,
)

# ============================================================
# CONSTANTS
# ============================================================

SEMANTIC_CONFIG_NAME = "support-semantic-config"
KNOWLEDGE_SOURCE_NAME = "support-policy-ks"
KNOWLEDGE_BASE_NAME = "support-policy-kb"


# ============================================================
# CONFIGURATION
# ============================================================

def load_configuration():
    """
    Load configuration values from .env.
    """

    load_dotenv()

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")

    index_name = os.getenv(
        "INTEGRATED_SEARCH_INDEX_NAME",
        "support-integrated-index",
    )

    if not search_endpoint:
        raise ValueError(
            "AZURE_SEARCH_ENDPOINT is not set in .env"
        )

    return search_endpoint, index_name


# ============================================================
# CREATE SEARCH CLIENT
# ============================================================

def create_search_client(search_endpoint,credential):

    index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=credential,
    )

    return index_client


# ============================================================
# STEP 1 - SEMANTIC CONFIGURATION
# ============================================================

def configure_semantic_search(index_client, index_name):
    """
    Add semantic configuration to the existing Search index.

    title   -> identifies the document
    content -> main natural-language content used by
               semantic ranking
    """

    print("\n==========================================")
    print("STEP 1 - CONFIGURE SEMANTIC SEARCH")
    print("==========================================")

    print(f"\nLoading index: {index_name}")

    index = index_client.get_index(index_name)

    print("Existing index loaded.")

    # --------------------------------------------------------
    # Define which fields semantic ranking should prioritize.
    # --------------------------------------------------------

    semantic_configuration = SemanticConfiguration(
        name=SEMANTIC_CONFIG_NAME,
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(
                field_name="title"
            ),
            content_fields=[
                SemanticField(
                    field_name="content"
                )
            ],
        ),
    )

    # --------------------------------------------------------
    # Attach semantic configuration to the index.
    # --------------------------------------------------------

    index.semantic_search = SemanticSearch(
        default_configuration_name=SEMANTIC_CONFIG_NAME,
        configurations=[
            semantic_configuration
        ],
    )

    print("Updating index...")

    index_client.create_or_update_index(index)

    print("Index updated successfully.")

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    verified_index = index_client.get_index(index_name)

    if verified_index.semantic_search:
        print(
            "Default semantic configuration:",
            verified_index.semantic_search.default_configuration_name,
        )

        print("Semantic configurations:")

        for configuration in (
            verified_index.semantic_search.configurations
        ):
            print(f"  - {configuration.name}")

    else:
        raise RuntimeError(
            "Semantic configuration was not created."
        )

    print("\nSTEP 1 COMPLETED")


# ============================================================
# STEP 2 - KNOWLEDGE SOURCE
# ============================================================

def create_knowledge_source(index_client, index_name):
    """
    Create a Knowledge Source that exposes our existing
    Search index to a Knowledge Base.
    """

    print("\n==========================================")
    print("STEP 2 - CREATE KNOWLEDGE SOURCE")
    print("==========================================")

    knowledge_source = SearchIndexKnowledgeSource(
        name=KNOWLEDGE_SOURCE_NAME,

        description=(
            "Company support policy knowledge source containing "
            "VPN, password, and laptop policies."
        ),

        search_index_parameters=SearchIndexKnowledgeSourceParameters(

            # Which Search index contains the knowledge?
            search_index_name=index_name,

            # Which semantic configuration should be used?
            semantic_configuration_name=SEMANTIC_CONFIG_NAME,

            # Which fields should retrieval search?
            search_fields=[
                SearchIndexFieldReference(
                    name="content"
                )
            ],

            # Which metadata fields should be returned
            # with references/citations?
            source_data_fields=[
                SearchIndexFieldReference(
                    name="chunk_id"
                ),
                SearchIndexFieldReference(
                    name="title"
                ),
                SearchIndexFieldReference(
                    name="source"
                ),
            ],
        ),
    )

    print(
        f"\nCreating knowledge source: "
        f"{KNOWLEDGE_SOURCE_NAME}"
    )

    index_client.create_or_update_knowledge_source(
        knowledge_source=knowledge_source
    )

    print("Knowledge source created successfully.")

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    verified_ks = index_client.get_knowledge_source(
        KNOWLEDGE_SOURCE_NAME
    )

    print(f"Knowledge Source : {verified_ks.name}")

    print(
        "Search Index     :",
        verified_ks.search_index_parameters.search_index_name,
    )

    print(
        "Semantic Config  :",
        verified_ks.search_index_parameters.semantic_configuration_name,
    )

    print("\nSTEP 2 COMPLETED")


# ============================================================
# STEP 3 - KNOWLEDGE BASE
# ============================================================

def create_knowledge_base(index_client):
    """
    Create a Knowledge Base using our Knowledge Source.

    With the stable 2026-04-01 API:
    - Retrieval is extractive by default.
    - output_mode is not configured on KnowledgeBase.
    - retrieval_reasoning_effort is not configured on KnowledgeBase.
    """

    print("\n==========================================")
    print("STEP 3 - CREATE KNOWLEDGE BASE")
    print("==========================================")

    knowledge_base = KnowledgeBase(
        name=KNOWLEDGE_BASE_NAME,

        knowledge_sources=[
            KnowledgeSourceReference(
                name=KNOWLEDGE_SOURCE_NAME
            )
        ],
    )

    print(
        f"\nCreating knowledge base: "
        f"{KNOWLEDGE_BASE_NAME}"
    )

    index_client.create_or_update_knowledge_base(
        knowledge_base=knowledge_base
    )

    print("Knowledge base created successfully.")

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    verified_kb = index_client.get_knowledge_base(
        KNOWLEDGE_BASE_NAME
    )

    print(f"Knowledge Base : {verified_kb.name}")

    print("Knowledge Sources:")

    for source in verified_kb.knowledge_sources:
        print(f"  - {source.name}")

    print("\nSTEP 3 COMPLETED")

def retrieve_from_knowledge_base(
    search_endpoint,
    credential,
):
    """
    Retrieve relevant information from the Knowledge Base.

    Stable API 2026-04-01:
    - Uses intents instead of messages
    - Performs minimal/extractive retrieval
    - Does not perform LLM query planning
    """

    print("\n==========================================")
    print("STEP 4 - RETRIEVE FROM KNOWLEDGE BASE")
    print("==========================================")

    # --------------------------------------------------------
    # Create Knowledge Base retrieval client
    # --------------------------------------------------------

    retrieval_client = KnowledgeBaseRetrievalClient(
        endpoint=search_endpoint,
        knowledge_base_name=KNOWLEDGE_BASE_NAME,
        credential=credential,
    )

    # --------------------------------------------------------
    # Question
    # --------------------------------------------------------

    question = (
        "Compare VPN and password policies. "
        "When does each expire and when are users warned?"
    )

    print(f"\nQuestion:\n{question}")

    # --------------------------------------------------------
    # Stable 2026-04-01 retrieval request
    #
    # IMPORTANT:
    # Stable API uses INTENTS, not MESSAGES.
    # --------------------------------------------------------

    request = KnowledgeBaseRetrievalRequest(
        intents=[
            KnowledgeRetrievalSemanticIntent(
                search=question
            )
        ],

        knowledge_source_params=[
            SearchIndexKnowledgeSourceParams(
                knowledge_source_name=KNOWLEDGE_SOURCE_NAME,
            )
        ],

        include_activity=True,
    )

    # --------------------------------------------------------
    # Execute retrieval
    # --------------------------------------------------------

    print("\nRetrieving from Knowledge Base...")

    result = retrieval_client.retrieve(request)

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    print("\n==========================================")
    print("RESPONSE")
    print("==========================================")

    if result.response:
        for response_message in result.response:
            for content_item in response_message.content:

                if hasattr(content_item, "text"):
                    print(content_item.text)
                else:
                    print(content_item)
    else:
        print("No response returned.")

    # --------------------------------------------------------
    # ACTIVITY
    # --------------------------------------------------------

    print("\n==========================================")
    print("ACTIVITY")
    print("==========================================")

    if result.activity:
        for activity in result.activity:
            print(activity)
            print("------------------------------------------")
    else:
        print("No activity returned.")

    # --------------------------------------------------------
    # REFERENCES
    # --------------------------------------------------------

    print("\n==========================================")
    print("REFERENCES")
    print("==========================================")

    if result.references:
        for reference in result.references:
            print(reference)
            print("------------------------------------------")
    else:
        print("No references returned.")

    print("\nSTEP 4 COMPLETED")
    
# ============================================================
# MAIN
# ============================================================

def main():

    print("==========================================")
    print("AZURE AI SEARCH - AGENTIC RETRIEVAL")
    print("==========================================")

    search_endpoint, index_name = load_configuration()

    print(f"\nSearch Endpoint : {search_endpoint}")
    print(f"Search Index    : {index_name}")

    credential = DefaultAzureCredential()

    index_client = create_search_client(
        search_endpoint,
        credential,
    )

    configure_semantic_search(
        index_client,
        index_name,
    )

    create_knowledge_source(
        index_client,
        index_name,
    )

    create_knowledge_base(
        index_client
    )

    # STEP 4
    retrieve_from_knowledge_base(
        search_endpoint,
        credential,
    )

    print("\n==========================================")
    print("AGENTIC RETRIEVAL TEST COMPLETED")
    print("==========================================")


if __name__ == "__main__":
    main()

