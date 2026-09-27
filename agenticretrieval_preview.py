import json
import os

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizerParameters,
    KnowledgeBase,
    KnowledgeBaseAzureOpenAIModel,
    KnowledgeSourceReference,
)

from azure.search.documents.knowledgebases import (
    KnowledgeBaseRetrievalClient,
)

from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalLowReasoningEffort,
)


# ============================================================
# CONSTANTS
# ============================================================

KNOWLEDGE_SOURCE_NAME = "support-policy-ks"

# Use a DIFFERENT KB so we don't overwrite our working
# stable Knowledge Base.
PREVIEW_KNOWLEDGE_BASE_NAME = "support-policy-kb-preview"


# ============================================================
# LOAD CONFIGURATION
# ============================================================

def load_configuration():
    load_dotenv()

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    agentic_model_name = os.getenv(
        "AGENTIC_MODEL_NAME",
        "gpt-5-mini"
    )

    agentic_model_deployment = os.getenv(
        "AGENTIC_MODEL_DEPLOYMENT_NAME"
    )

    if not search_endpoint:
        raise ValueError(
            "AZURE_SEARCH_ENDPOINT is missing from .env"
        )

    if not azure_openai_endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT is missing from .env"
        )

    if not agentic_model_deployment:
        raise ValueError(
            "AGENTIC_MODEL_DEPLOYMENT_NAME is missing from .env"
        )

    return (
        search_endpoint,
        azure_openai_endpoint,
        agentic_model_name,
        agentic_model_deployment,
    )


# ============================================================
# CREATE PREVIEW KNOWLEDGE BASE
# ============================================================

def create_preview_knowledge_base(
    search_endpoint,
    azure_openai_endpoint,
    model_name,
    model_deployment,
    credential,
):
    print("\n==========================================")
    print("STEP 1 - CREATE PREVIEW KNOWLEDGE BASE")
    print("==========================================")

    index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=credential,
    )

    # --------------------------------------------------------
    # Configure the LLM used by the Knowledge Base.
    #
    # IMPORTANT:
    # This is NOT our embedding model.
    #
    # gpt-5-mini is being used for:
    #     Query planning / reasoning
    # --------------------------------------------------------

    openai_parameters = AzureOpenAIVectorizerParameters(
        resource_url=azure_openai_endpoint,
        deployment_name=model_deployment,
        model_name=model_name,
    )

    planning_model = KnowledgeBaseAzureOpenAIModel(
        azure_open_ai_parameters=openai_parameters
    )

    # --------------------------------------------------------
    # Create a separate preview Knowledge Base.
    # --------------------------------------------------------

    knowledge_base = KnowledgeBase(
        name=PREVIEW_KNOWLEDGE_BASE_NAME,

        models=[
            planning_model
        ],

        knowledge_sources=[
            KnowledgeSourceReference(
                name=KNOWLEDGE_SOURCE_NAME
            )
        ],

        # Keep retrieval output extractive for now.
        #
        # We want to inspect what retrieval actually found
        # before enabling answer synthesis.
         output_mode="extractiveData",
    )

    print(
        f"Creating preview Knowledge Base: "
        f"{PREVIEW_KNOWLEDGE_BASE_NAME}"
    )

    index_client.create_or_update_knowledge_base(
        knowledge_base=knowledge_base
    )

    print("Preview Knowledge Base created successfully.")


# ============================================================
# RUN AGENTIC RETRIEVAL
# ============================================================

def run_agentic_retrieval(
    search_endpoint,
    credential,
):
    print("\n==========================================")
    print("STEP 2 - AGENTIC QUERY PLANNING")
    print("==========================================")

    retrieval_client = KnowledgeBaseRetrievalClient(
        endpoint=search_endpoint,
        knowledge_base_name=PREVIEW_KNOWLEDGE_BASE_NAME,
        credential=credential,
    )

    question = (
        "Compare VPN and password policies. "
        "When does each expire and when are users warned?"
    )

    print("\nQuestion:")
    print(question)

    # --------------------------------------------------------
    # PREVIEW DIFFERENCE
    #
    # Stable:
    #     intents=[...]
    #
    # Preview:
    #     messages=[...]
    #
    # The conversation can now participate in query planning.
    # --------------------------------------------------------

    request = KnowledgeBaseRetrievalRequest(
        messages=[
            KnowledgeBaseMessage(
                role="user",
                content=[
                    KnowledgeBaseMessageTextContent(
                        text=question
                    )
                ],
            )
        ],

        # ----------------------------------------------------
        # THIS is what turns on LLM query planning.
        #
        # minimal -> no LLM query planning
        # low     -> LLM query planning
        # ----------------------------------------------------

        retrieval_reasoning_effort=(
            KnowledgeRetrievalLowReasoningEffort()
        ),
    )

    print("\nRunning agentic retrieval...")

    result = retrieval_client.retrieve(
        retrieval_request=request
    )

    print("\nAgentic retrieval completed.")

    return result


# ============================================================
# DISPLAY RESPONSE
# ============================================================

def display_response(result):
    print("\n==========================================")
    print("RESPONSE")
    print("==========================================")

    if not result.response:
        print("No response returned.")
        return

    for response in result.response:
        for content in response.content:

            if hasattr(content, "text"):
                print(content.text)
            else:
                print(content)


# ============================================================
# DISPLAY ACTIVITY
# ============================================================

def display_activity(result):
    print("\n==========================================")
    print("ACTIVITY - MOST IMPORTANT FOR THIS TEST")
    print("==========================================")

    if not result.activity:
        print("No activity returned.")
        return

    for activity in result.activity:

        if hasattr(activity, "as_dict"):
            activity_dict = activity.as_dict()
        else:
            activity_dict = activity

        print(
            json.dumps(
                activity_dict,
                indent=2,
                default=str,
            )
        )

        print("------------------------------------------")


# ============================================================
# DISPLAY REFERENCES
# ============================================================

def display_references(result):
    print("\n==========================================")
    print("REFERENCES")
    print("==========================================")

    if not result.references:
        print("No references returned.")
        return

    for reference in result.references:

        if hasattr(reference, "as_dict"):
            reference_dict = reference.as_dict()
        else:
            reference_dict = reference

        print(
            json.dumps(
                reference_dict,
                indent=2,
                default=str,
            )
        )

        print("------------------------------------------")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n==========================================")
    print("AZURE AI SEARCH")
    print("AGENTIC RETRIEVAL - PREVIEW")
    print("==========================================")

    (
        search_endpoint,
        azure_openai_endpoint,
        model_name,
        model_deployment,
    ) = load_configuration()

    print(f"\nSearch Endpoint : {search_endpoint}")
    print(f"Planning Model  : {model_name}")
    print(f"Deployment      : {model_deployment}")

    credential = DefaultAzureCredential()

    # --------------------------------------------------------
    # Step 1
    # Create preview Knowledge Base with planning LLM
    # --------------------------------------------------------

    create_preview_knowledge_base(
        search_endpoint=search_endpoint,
        azure_openai_endpoint=azure_openai_endpoint,
        model_name=model_name,
        model_deployment=model_deployment,
        credential=credential,
    )

    # --------------------------------------------------------
    # Step 2
    # Execute agentic retrieval
    # --------------------------------------------------------

    result = run_agentic_retrieval(
        search_endpoint=search_endpoint,
        credential=credential,
    )

    # --------------------------------------------------------
    # Step 3
    # Inspect what Azure actually did
    # --------------------------------------------------------

    display_response(result)
    display_activity(result)
    display_references(result)

    print("\n==========================================")
    print("PREVIEW AGENTIC RETRIEVAL COMPLETED")
    print("==========================================")


if __name__ == "__main__":
    main()