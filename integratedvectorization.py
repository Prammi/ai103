import os
import time

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

from azure.search.documents import SearchClient
from azure.search.documents.indexes import (
    SearchIndexClient,
    SearchIndexerClient,
)

from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    SearchIndex,

    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,

    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer,

    SearchIndexerSkillset,
    SplitSkill,
    AzureOpenAIEmbeddingSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,

    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,

    SearchIndexer,
)

from azure.search.documents.models import VectorizableTextQuery


# ============================================================
# 1. LOAD CONFIGURATION
# ============================================================

def load_configuration():
    load_dotenv()

    config = {
        "search_endpoint": os.getenv("AZURE_SEARCH_ENDPOINT"),

        "storage_account_name": os.getenv(
            "AZURE_STORAGE_ACCOUNT_NAME"
        ),
        "storage_container_name": os.getenv(
            "AZURE_STORAGE_CONTAINER_NAME",
            "support-policies",
        ),

        "azure_openai_endpoint": os.getenv(
            "AZURE_OPENAI_ENDPOINT"
        ),
        "embedding_deployment_name": os.getenv(
            "EMBEDDING_DEPLOYMENT_NAME"
        ),
        "embedding_model_name": os.getenv(
            "EMBEDDING_MODEL_NAME",
            "text-embedding-3-small",
        ),
        "embedding_dimensions": int(
            os.getenv("EMBEDDING_DIMENSIONS", "1536")
        ),

        "index_name": os.getenv(
            "INTEGRATED_SEARCH_INDEX_NAME",
            "support-integrated-index",
        ),
        "datasource_name": os.getenv(
            "INTEGRATED_SEARCH_DATASOURCE_NAME",
            "support-integrated-datasource",
        ),
        "skillset_name": os.getenv(
            "INTEGRATED_SEARCH_SKILLSET_NAME",
            "support-integrated-skillset",
        ),
        "indexer_name": os.getenv(
            "INTEGRATED_SEARCH_INDEXER_NAME",
            "support-integrated-indexer",
        ),
    }

    required_values = [
        "search_endpoint",
        "storage_account_name",
        "azure_openai_endpoint",
        "embedding_deployment_name",
    ]

    missing = [
        key
        for key in required_values
        if not config[key]
    ]

    if missing:
        raise ValueError(
            "Missing environment variables for: "
            + ", ".join(missing)
        )

    return config


# ============================================================
# 2. CREATE CLIENTS
# ============================================================

def create_clients(config):
    credential = DefaultAzureCredential()

    index_client = SearchIndexClient(
        endpoint=config["search_endpoint"],
        credential=credential,
    )

    indexer_client = SearchIndexerClient(
        endpoint=config["search_endpoint"],
        credential=credential,
    )

    return credential, index_client, indexer_client


# ============================================================
# 3. CREATE BLOB DATA SOURCE
# ============================================================

def create_data_source(config, indexer_client):
    print("\nCreating Blob Storage data source...")

    storage_resource_id = (
        f"/subscriptions/{os.getenv('AZURE_SUBSCRIPTION_ID')}"
        f"/resourceGroups/{os.getenv('AZURE_STORAGE_RESOURCE_GROUP')}"
        f"/providers/Microsoft.Storage/storageAccounts/"
        f"{config['storage_account_name']}"
    )

    connection_string = (
        f"ResourceId={storage_resource_id};"
    )

    container = SearchIndexerDataContainer(
        name=config["storage_container_name"]
    )

    data_source = SearchIndexerDataSourceConnection(
        name=config["datasource_name"],
        type="azureblob",
        connection_string=connection_string,
        container=container,
    )

    result = (
        indexer_client
        .create_or_update_data_source_connection(
            data_source
        )
    )

    print(f"Data source ready: {result.name}")


# ============================================================
# 4. CREATE VECTOR INDEX + QUERY-TIME VECTORIZER
# ============================================================

def create_search_index(config, index_client):
    print("\nCreating vector search index...")

    vectorizer_name = "support-openai-vectorizer"
    vector_profile_name = "support-vector-profile"
    algorithm_name = "support-hnsw"

    fields = [
        SearchField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
            analyzer_name="keyword",
        ),

        SearchField(
            name="parent_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),

        SearchField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
        ),

        SearchField(
            name="source",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
        ),

        SearchField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
        ),

        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.Single
            ),
            searchable=True,
            vector_search_dimensions=config[
                "embedding_dimensions"
            ],
            vector_search_profile_name=vector_profile_name,
        ),
    ]

    vectorizer = AzureOpenAIVectorizer(
        vectorizer_name=vectorizer_name,
        parameters=AzureOpenAIVectorizerParameters(
            resource_url=config["azure_openai_endpoint"],
            deployment_name=config[
                "embedding_deployment_name"
            ],
            model_name=config["embedding_model_name"],
        ),
    )

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=algorithm_name
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=vector_profile_name,
                algorithm_configuration_name=algorithm_name,
                vectorizer_name=vectorizer_name,
            )
        ],
        vectorizers=[
            vectorizer
        ],
    )

    index = SearchIndex(
        name=config["index_name"],
        fields=fields,
        vector_search=vector_search,
    )

    result = index_client.create_or_update_index(index)

    print(f"Index ready: {result.name}")


# ============================================================
# 5. CREATE SKILLSET
# ============================================================

def create_skillset(config, indexer_client):
    print("\nCreating skillset...")

    # --------------------------------------------------------
    # Split the original document into chunks.
    # --------------------------------------------------------

    split_skill = SplitSkill(
        name="split-policy-documents",
        description="Split company policy documents into chunks.",
        context="/document",
        text_split_mode="pages",
        maximum_page_length=1000,
        page_overlap_length=200,
        inputs=[
            InputFieldMappingEntry(
                name="text",
                source="/document/content",
            )
        ],
        outputs=[
            OutputFieldMappingEntry(
                name="textItems",
                target_name="pages",
            )
        ],
    )

    # --------------------------------------------------------
    # Generate an embedding for EACH chunk.
    # --------------------------------------------------------

    embedding_skill = AzureOpenAIEmbeddingSkill(
        name="embed-policy-chunks",
        description="Generate embeddings for policy chunks.",
        context="/document/pages/*",

        resource_url=config["azure_openai_endpoint"],

        deployment_name=config[
            "embedding_deployment_name"
        ],

        model_name=config[
            "embedding_model_name"
        ],

        dimensions=config[
            "embedding_dimensions"
        ],

        inputs=[
            InputFieldMappingEntry(
                name="text",
                source="/document/pages/*",
            )
        ],

        outputs=[
            OutputFieldMappingEntry(
                name="embedding",
                target_name="vector",
            )
        ],
    )

    # --------------------------------------------------------
    # Index Projection
    #
    # One Blob:
    # vpn-policy.txt
    #
    # can become:
    #
    # chunk 1 -> index record
    # chunk 2 -> index record
    # chunk 3 -> index record
    # --------------------------------------------------------

    projection_selector = (
        SearchIndexerIndexProjectionSelector(
            target_index_name=config["index_name"],

            parent_key_field_name="parent_id",

            source_context="/document/pages/*",

            mappings=[
                InputFieldMappingEntry(
                    name="content",
                    source="/document/pages/*",
                ),

                InputFieldMappingEntry(
                    name="contentVector",
                    source="/document/pages/*/vector",
                ),

                InputFieldMappingEntry(
                    name="title",
                    source="/document/metadata_storage_name",
                ),

                InputFieldMappingEntry(
                    name="source",
                    source="/document/metadata_storage_name",
                ),
            ],
        )
    )

    index_projection = SearchIndexerIndexProjection(
        selectors=[
            projection_selector
        ],

        parameters=SearchIndexerIndexProjectionsParameters(
            projection_mode="skipIndexingParentDocuments"
        ),
    )

    skillset = SearchIndexerSkillset(
        name=config["skillset_name"],
        description=(
            "Chunk and vectorize company support policies."
        ),
        skills=[
            split_skill,
            embedding_skill,
        ],
        index_projection=index_projection,
    )

    result = indexer_client.create_or_update_skillset(
        skillset
    )

    print(f"Skillset ready: {result.name}")


# ============================================================
# 6. CREATE INDEXER
# ============================================================

def create_indexer(config, indexer_client):
    print("\nCreating indexer...")

    indexer = SearchIndexer(
        name=config["indexer_name"],

        data_source_name=config[
            "datasource_name"
        ],

        target_index_name=config[
            "index_name"
        ],

        skillset_name=config[
            "skillset_name"
        ],

        field_mappings=[],
        output_field_mappings=[],
    )

    result = indexer_client.create_or_update_indexer(
        indexer
    )

    print(f"Indexer ready: {result.name}")


# ============================================================
# 7. RUN INDEXER
# ============================================================

def run_indexer(config, indexer_client):
    print("\nRunning indexer...")

    indexer_client.run_indexer(
        config["indexer_name"]
    )

    print("Indexer started.")


# ============================================================
# 8. WAIT FOR INDEXER
# ============================================================

def wait_for_indexer(config, indexer_client):
    print("\nWaiting for indexer to complete...")

    for attempt in range(30):
        time.sleep(5)

        status = indexer_client.get_indexer_status(
            config["indexer_name"]
        )

        last_result = status.last_result

        if last_result is None:
            print("Indexer has not reported a result yet...")
            continue

        current_status = last_result.status

        print(f"\nIndexer status: {current_status}")

        # ----------------------------------------------------
        # Print overall error message
        # ----------------------------------------------------
        if last_result.error_message:
            print("\nOVERALL ERROR MESSAGE:")
            print(last_result.error_message)

        # ----------------------------------------------------
        # Print detailed errors
        # ----------------------------------------------------
        if last_result.errors:
            print("\nDETAILED ERRORS:")

            for i, error in enumerate(
                last_result.errors,
                start=1
            ):
                print(f"\n--- ERROR {i} ---")

                print(
                    f"Key     : "
                    f"{getattr(error, 'key', None)}"
                )

                print(
                    f"Name    : "
                    f"{getattr(error, 'name', None)}"
                )

                print(
                    f"Message : "
                    f"{getattr(error, 'message', None)}"
                )

                print(
                    f"Details : "
                    f"{getattr(error, 'details', None)}"
                )

        # ----------------------------------------------------
        # Print warnings too
        # ----------------------------------------------------
        if last_result.warnings:
            print("\nWARNINGS:")

            for i, warning in enumerate(
                last_result.warnings,
                start=1
            ):
                print(f"\n--- WARNING {i} ---")

                print(
                    f"Name    : "
                    f"{getattr(warning, 'name', None)}"
                )

                print(
                    f"Message : "
                    f"{getattr(warning, 'message', None)}"
                )

                print(
                    f"Details : "
                    f"{getattr(warning, 'details', None)}"
                )

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------
        if current_status == "success":
            print("\nIndexer completed successfully.")

            print(
                f"Items processed: "
                f"{last_result.item_count}"
            )

            print(
                f"Items failed: "
                f"{last_result.failed_item_count}"
            )

            return

        # ----------------------------------------------------
        # Failure
        # ----------------------------------------------------
        if current_status in [
            "transientFailure",
            "persistentFailure",
        ]:
            print("\nIndexer execution failed.")

            raise RuntimeError(
                "Integrated vectorization indexer failed. "
                "See the Azure error details printed above."
            )

    raise TimeoutError(
        "Indexer did not finish within the expected time."
    )

# ============================================================
# 9. INSPECT GENERATED CHUNKS
# ============================================================

def inspect_index(config, credential):
    print("\nInspecting generated chunks...")

    search_client = SearchClient(
        endpoint=config["search_endpoint"],
        index_name=config["index_name"],
        credential=credential,
    )

    results = search_client.search(
        search_text="*",
        select=[
            "chunk_id",
            "parent_id",
            "title",
            "source",
            "content",
        ],
        top=20,
    )

    count = 0

    for result in results:
        count += 1

        print("\n-----------------------------------")
        print(f"Chunk ID : {result.get('chunk_id')}")
        print(f"Parent ID: {result.get('parent_id')}")
        print(f"Title    : {result.get('title')}")
        print(f"Source   : {result.get('source')}")
        print(f"Content  : {result.get('content')}")

    print(
        f"\nTotal chunks displayed: {count}"
    )


# ============================================================
# 10. TEXT-BASED VECTOR QUERY
# ============================================================

def test_integrated_vectorization(config, credential):
    print("\nTesting query-time integrated vectorization...")

    search_client = SearchClient(
        endpoint=config["search_endpoint"],
        index_name=config["index_name"],
        credential=credential,
    )

    question = (
        "How often do VPN credentials need to be renewed?"
    )

    # IMPORTANT:
    #
    # We are NOT generating the query embedding ourselves.
    #
    # Azure AI Search receives TEXT.
    # The configured Azure OpenAI vectorizer converts
    # the text into a query vector automatically.

    vector_query = VectorizableTextQuery(
        text=question,
        k_nearest_neighbors=3,
        fields="contentVector",
        
    )

    results = search_client.search(
        search_text=None,
        vector_queries=[
            vector_query
        ],
        select=[
            "title",
            "source",
            "content",
        ],
        top=3,
    )

    print(f"\nQuestion: {question}")

    print("\nResults:")

    for result in results:
        print("\n-----------------------------------")
        print(f"Score  : {result.get('@search.score')}")
        print(f"Title  : {result.get('title')}")
        print(f"Source : {result.get('source')}")
        print(f"Content: {result.get('content')}")


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        "\n=========================================="
    )
    print(
        "AZURE AI SEARCH - INTEGRATED VECTORIZATION"
    )
    print(
        "=========================================="
    )

    config = load_configuration()

    credential, index_client, indexer_client = (
        create_clients(config)
    )

    # --------------------------------------------------------
    # Infrastructure setup
    # --------------------------------------------------------

    create_data_source(
        config,
        indexer_client,
    )

    create_search_index(
        config,
        index_client,
    )

    create_skillset(
        config,
        indexer_client,
    )

    create_indexer(
        config,
        indexer_client,
    )

    # --------------------------------------------------------
    # Run ingestion
    # --------------------------------------------------------

    run_indexer(
        config,
        indexer_client,
    )

    wait_for_indexer(
        config,
        indexer_client,
    )

    # --------------------------------------------------------
    # Verify generated chunks
    # --------------------------------------------------------

    inspect_index(
        config,
        credential,
    )

    # --------------------------------------------------------
    # Test query-time vectorization
    # --------------------------------------------------------

    test_integrated_vectorization(
        config,
        credential,
    )


if __name__ == "__main__":
    main()