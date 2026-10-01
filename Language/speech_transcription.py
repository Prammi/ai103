import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI


def main():
    # Clear terminal
    os.system("cls" if os.name == "nt" else "clear")

    # ---------------------------------------------------------
    # Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    transcribe_model = os.getenv("TRANSCRIBE_MODEL_DEPLOYMENT_NAME")

    if not azure_openai_endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT is not set in .env")

    if not transcribe_model:
        raise ValueError(
            "TRANSCRIBE_MODEL_DEPLOYMENT_NAME is not set in .env"
        )

    # ---------------------------------------------------------
    # Authenticate using Microsoft Entra ID
    # ---------------------------------------------------------
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )

    # ---------------------------------------------------------
    # Create Azure OpenAI client
    # ---------------------------------------------------------
    client = AzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2025-04-01-preview",
    )

    # ---------------------------------------------------------
    # Audio file to transcribe
    # ---------------------------------------------------------
    audio_file_path = "hyderabad_temperature_question.wav"

    print("Audio file:")
    print(audio_file_path)

    print("\nTranscribing...\n")

    # ---------------------------------------------------------
    # Speech → Text
    # ---------------------------------------------------------
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=transcribe_model,
            file=audio_file,
        )

    # ---------------------------------------------------------
    # Display result
    # ---------------------------------------------------------
    print("Transcription:")
    print(transcription.text)


if __name__ == "__main__":
    main()