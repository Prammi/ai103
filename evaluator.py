import os

from azure.ai.evaluation import (
    GroundednessEvaluator,
    RelevanceEvaluator,
    RetrievalEvaluator,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main():
    # ---------------------------------------------------------
    # Load environment variables
    # ---------------------------------------------------------

    load_dotenv()

    azure_openai_endpoint = os.getenv(
        "AZURE_OPENAI_ENDPOINT"
    )

    evaluation_model_deployment = os.getenv(
        "EVALUATION_MODEL_DEPLOYMENT_NAME"
    )

    if not azure_openai_endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT is missing from .env"
        )

    if not evaluation_model_deployment:
        raise ValueError(
            "EVALUATION_MODEL_DEPLOYMENT_NAME is missing from .env"
        )
    # ---------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------

    credential = DefaultAzureCredential()

    # ---------------------------------------------------------
    # Evaluator model configuration
    # ---------------------------------------------------------

    model_config = {
        "azure_endpoint": azure_openai_endpoint,
        "azure_deployment": evaluation_model_deployment,
    }

    # ---------------------------------------------------------
    # Create evaluators
    # ---------------------------------------------------------

    retrieval_evaluator = RetrievalEvaluator(
        model_config=model_config,
        credential=credential,
        is_reasoning_model=True,
    )

    groundedness_evaluator = GroundednessEvaluator(
        model_config=model_config,
        credential=credential,
        is_reasoning_model=True,
    )

    relevance_evaluator = RelevanceEvaluator(
        model_config=model_config,
        credential=credential,
        is_reasoning_model=True,
    )

    # ---------------------------------------------------------
    # Data from our RAG application
    # ---------------------------------------------------------

    query = (
        "When do VPN credentials expire?"
    )

    context = (
        "Corporate VPN Policy. "
        "Employees working outside the corporate network "
        "must connect through the company VPN. "
        "VPN access requires multi-factor authentication. "
        "VPN credentials expire every 90 days."
    )

    response = (
        "VPN credentials expire every 30 days."
    )

    # ---------------------------------------------------------
    # Evaluate retrieval
    # ---------------------------------------------------------

    retrieval_result = retrieval_evaluator(
        query=query,
        context=context,
    )

    # ---------------------------------------------------------
    # Evaluate groundedness
    # ---------------------------------------------------------

    groundedness_result = groundedness_evaluator(
        query=query,
        context=context,
        response=response,
    )

    # ---------------------------------------------------------
    # Evaluate relevance
    # ---------------------------------------------------------

    relevance_result = relevance_evaluator(
        query=query,
        response=response,
    )

    # ---------------------------------------------------------
    # Display results
    # ---------------------------------------------------------

    print("\n======================================")
    print("RAG EVALUATION RESULTS")
    print("======================================")

    print("\nRetrieval:")
    print(retrieval_result)

    print("\nGroundedness:")
    print(groundedness_result)

    print("\nRelevance:")
    print(relevance_result)


if __name__ == "__main__":
    main()