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

# Separate Knowledge Base specifically for answer synthesis.
KNOWLEDGE_BASE_NAME = "support-policy-kb-synthesis"


# ============================================================
# LOAD CONFIGURATION
# ============================================================

def load_configuration():
    load_dotenv()

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    model_name = os.getenv(
        "AGENTIC_MODEL_NAME",
        "gpt-5-mini",
    )

    model_deployment = os.getenv(
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

    if not model_deployment:
        raise ValueError(
            "AGENTIC_MODEL_DEPLOYMENT_NAME is missing from .env"
        )

    return (
        search_endpoint,
        azure_openai_endpoint,
        model_name,
        model_deployment,
    )


# ============================================================
# CREATE KNOWLEDGE BASE
# ============================================================

def create_synthesis_knowledge_base(
    search_endpoint,
    azure_openai_endpoint,
    model_name,
    model_deployment,
    credential,
):
    print("\n==========================================")
    print("STEP 1 - CREATE SYNTHESIS KNOWLEDGE BASE")
    print("==========================================")

    index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=credential,
    )

    # --------------------------------------------------------
    # Configure GPT-5-mini for the Knowledge Base.
    #
    # This model can participate in:
    #
    # 1. Query planning
    # 2. Answer synthesis
    #
    # It is NOT the embedding model.
    # --------------------------------------------------------

    openai_parameters = AzureOpenAIVectorizerParameters(
        resource_url=azure_openai_endpoint,
        deployment_name=model_deployment,
        model_name=model_name,
    )

    knowledge_base_model = KnowledgeBaseAzureOpenAIModel(
        azure_open_ai_parameters=openai_parameters
    )

    # --------------------------------------------------------
    # Create Knowledge Base
    #
    # IMPORTANT:
    #
    # output_mode="answerSynthesis"
    #
    # tells the Knowledge Base that we want a natural-language
    # answer rather than only the raw retrieved documents.
    # --------------------------------------------------------

    knowledge_base = KnowledgeBase(
        name=KNOWLEDGE_BASE_NAME,

        models=[
            knowledge_base_model
        ],

        knowledge_sources=[
            KnowledgeSourceReference(
                name=KNOWLEDGE_SOURCE_NAME
            )
        ],

        output_mode="answerSynthesis",

        answer_instructions=(
            "Answer the user's question using only information "
            "from the retrieved company policy documents. "
            "Compare the policies clearly. "
            "Do not invent information that is not present "
            "in the retrieved documents."
        ),
    )

    print(
        f"Creating Knowledge Base: "
        f"{KNOWLEDGE_BASE_NAME}"
    )

    index_client.create_or_update_knowledge_base(
        knowledge_base=knowledge_base
    )

    print("Synthesis Knowledge Base created successfully.")

    # --------------------------------------------------------
    # Verify the Knowledge Base
    # --------------------------------------------------------

    verified_kb = index_client.get_knowledge_base(
        KNOWLEDGE_BASE_NAME
    )

    print(f"Knowledge Base : {verified_kb.name}")
    print(f"Output Mode    : {verified_kb.output_mode}")

    print("\nSTEP 1 COMPLETED")


# ============================================================
# RUN ANSWER SYNTHESIS
# ============================================================

def run_answer_synthesis(
    search_endpoint,
    credential,
):
    print("\n==========================================")
    print("STEP 2 - QUERY PLANNING + ANSWER SYNTHESIS")
    print("==========================================")

    retrieval_client = KnowledgeBaseRetrievalClient(
        endpoint=search_endpoint,
        knowledge_base_name=KNOWLEDGE_BASE_NAME,
        credential=credential,
    )

    question = (
        "Compare VPN and password policies. "
        "When does each expire and when are users warned?"
    )

    print("\nQuestion:")
    print(question)

    # --------------------------------------------------------
    # IMPORTANT
    #
    # We explicitly specify answerSynthesis HERE as well.
    #
    # This removes any ambiguity about which output mode
    # should be used for this particular request.
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

        retrieval_reasoning_effort=(
            KnowledgeRetrievalLowReasoningEffort()
        ),

        output_mode="answerSynthesis",

        include_activity=True,

        max_runtime_in_seconds=30,

        #max_output_size_in_tokens=6000,
    )

    print("\nRunning retrieval + answer synthesis...")

    result = retrieval_client.retrieve(
        retrieval_request=request
    )

    print("Retrieval + answer synthesis completed.")

    return result


# ============================================================
# DISPLAY FINAL ANSWER
# ============================================================

def display_answer(result):
    print("\n==========================================")
    print("FINAL SYNTHESIZED ANSWER")
    print("==========================================")

    if not result.response:
        print("No response returned.")
        return

    for response_message in result.response:

        if not response_message.content:
            continue

        for content_item in response_message.content:

            if hasattr(content_item, "text"):
                print(content_item.text)
            else:
                print(content_item)


# ============================================================
# DISPLAY ACTIVITY
# ============================================================

def display_activity(result):
    print("\n==========================================")
    print("ACTIVITY")
    print("==========================================")

    if not result.activity:
        print("No activity returned.")
        return

    for activity in result.activity:

        if hasattr(activity, "as_dict"):
            activity_data = activity.as_dict()
        else:
            activity_data = activity

        print(
            json.dumps(
                activity_data,
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
            reference_data = reference.as_dict()
        else:
            reference_data = reference

        print(
            json.dumps(
                reference_data,
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
    print("AGENTIC RETRIEVAL - ANSWER SYNTHESIS")
    print("==========================================")

    (
        search_endpoint,
        azure_openai_endpoint,
        model_name,
        model_deployment,
    ) = load_configuration()

    print(f"\nSearch Endpoint : {search_endpoint}")
    print(f"Model           : {model_name}")
    print(f"Deployment      : {model_deployment}")

    credential = DefaultAzureCredential()

    # --------------------------------------------------------
    # STEP 1
    # Create separate answer-synthesis Knowledge Base
    # --------------------------------------------------------

    create_synthesis_knowledge_base(
        search_endpoint=search_endpoint,
        azure_openai_endpoint=azure_openai_endpoint,
        model_name=model_name,
        model_deployment=model_deployment,
        credential=credential,
    )

    # --------------------------------------------------------
    # STEP 2
    # Run query planning + retrieval + answer synthesis
    # --------------------------------------------------------

    result = run_answer_synthesis(
        search_endpoint=search_endpoint,
        credential=credential,
    )

    # --------------------------------------------------------
    # STEP 3
    # Inspect everything
    # --------------------------------------------------------

    display_answer(result)
    display_activity(result)
    display_references(result)

    print("\n==========================================")
    print("ANSWER SYNTHESIS COMPLETED")
    print("==========================================")


if __name__ == "__main__":
    main()