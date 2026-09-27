import os

from azure.ai.textanalytics import TextAnalyticsClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main():
    # ---------------------------------------------------------
    # Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    language_endpoint = os.getenv("LANGUAGE_ENDPOINT")

    if not language_endpoint:
        raise ValueError("LANGUAGE_ENDPOINT is not set in .env")

    # ---------------------------------------------------------
    # Authenticate with Azure
    # ---------------------------------------------------------
    credential = DefaultAzureCredential()

    # ---------------------------------------------------------
    # Create Azure Language client
    # ---------------------------------------------------------
    language_client = TextAnalyticsClient(
        endpoint=language_endpoint,
        credential=credential,
    )

    # =========================================================
    # 1. LANGUAGE DETECTION
    # =========================================================
    print("\n--- LANGUAGE DETECTION ---")

    language_documents = [
        "Microsoft is building new AI solutions for customers in Hyderabad."
    ]

    language_results = language_client.detect_language(
        documents=language_documents
    )

    for document in language_results:
        if document.is_error:
            print(f"Error: {document.error}")
        else:
            print(f"Language: {document.primary_language.name}")
            print(f"ISO Code: {document.primary_language.iso6391_name}")
            print(
                f"Confidence: "
                f"{document.primary_language.confidence_score}"
            )

    # =========================================================
    # 2. NAMED ENTITY RECOGNITION (NER)
    # =========================================================
    print("\n--- NAMED ENTITY RECOGNITION ---")

    ner_documents = [
        "Satya Nadella works at Microsoft and visited Hyderabad in September."
    ]

    entity_results = language_client.recognize_entities(
        documents=ner_documents
    )

    for document in entity_results:
        if document.is_error:
            print(f"Error: {document.error}")
        else:
            for entity in document.entities:
                print(f"Text: {entity.text}")
                print(f"Category: {entity.category}")
                print(f"Subcategory: {entity.subcategory}")
                print(f"Confidence: {entity.confidence_score}")
                print()

    # =========================================================
    # 3. PII DETECTION
    # =========================================================
    print("\n--- PII DETECTION ---")

    pii_documents = [
        "My name is John Smith. "
        "My email is john.smith@example.com and "
        "my phone number is +1-425-555-0100. "
        "I work for Microsoft in Hyderabad."
    ]

    pii_results = language_client.recognize_pii_entities(
        documents=pii_documents
    )

    for document in pii_results:
        if document.is_error:
            print(f"Error: {document.error}")
        else:
            for entity in document.entities:
                print(f"Text: {entity.text}")
                print(f"Category: {entity.category}")
                print(f"Subcategory: {entity.subcategory}")
                print(f"Confidence: {entity.confidence_score}")
                print()

            print("Redacted Text:")
            print(document.redacted_text)

    # =========================================================
    # 4. SENTIMENT ANALYSIS
    # =========================================================
    print("\n--- SENTIMENT ANALYSIS ---")

    sentiment_documents = [
        "The new factory monitoring application is excellent. "
        "However, the customer support experience was terrible."
    ]

    sentiment_results = language_client.analyze_sentiment(
        documents=sentiment_documents
    )

    for document in sentiment_results:
        if document.is_error:
            print(f"Error: {document.error}")
        else:
            # Overall document sentiment
            print(f"Overall Sentiment: {document.sentiment}")
            print("Overall Confidence Scores:")
            print(
                f"  Positive: "
                f"{document.confidence_scores.positive}"
            )
            print(
                f"  Neutral: "
                f"{document.confidence_scores.neutral}"
            )
            print(
                f"  Negative: "
                f"{document.confidence_scores.negative}"
            )

            # Sentence-level sentiment
            print("\nSentence-level Sentiment:")

            for sentence in document.sentences:
                print(f"\nSentence: {sentence.text}")
                print(f"Sentiment: {sentence.sentiment}")
                print(
                    f"Positive: "
                    f"{sentence.confidence_scores.positive}"
                )
                print(
                    f"Neutral: "
                    f"{sentence.confidence_scores.neutral}"
                )
                print(
                    f"Negative: "
                    f"{sentence.confidence_scores.negative}"
                )


if __name__ == "__main__":
    main()