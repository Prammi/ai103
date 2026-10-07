import os

from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from dotenv import load_dotenv


def main():
    # Clear console
    os.system("cls" if os.name == "nt" else "clear")

    # Load environment variables
    load_dotenv()

    translator_endpoint = os.getenv("TRANSLATOR_ENDPOINT")
    translator_key = os.getenv("TRANSLATOR_KEY")
    translator_region = os.getenv("TRANSLATOR_REGION")

    # ---------------------------------------------------------
    # Validate configuration
    # ---------------------------------------------------------
    if not translator_endpoint:
        raise ValueError("TRANSLATOR_ENDPOINT is not set in .env")

    if not translator_key:
        raise ValueError("TRANSLATOR_KEY is not set in .env")

    if not translator_region:
        raise ValueError("TRANSLATOR_REGION is not set in .env")

    # ---------------------------------------------------------
    # Create Azure Translator client
    # ---------------------------------------------------------
    credential = AzureKeyCredential(translator_key)

    client = TextTranslationClient(
        endpoint=translator_endpoint,
        credential=credential,
        region=translator_region,
    )

    # ---------------------------------------------------------
    # Text to translate
    # ---------------------------------------------------------
    text = (
        "Microsoft Foundry provides tools "
        "for building intelligent applications."
    )

    source_language = "en"

    # hi = Hindi
    # fr = French
    target_languages = ["hi", "fr"]

    # Current SDK accepts a list of strings
    input_text = [text]

    # ---------------------------------------------------------
    # Translate
    # ---------------------------------------------------------
    try:
        response = client.translate(
            body=input_text,
            to_language=target_languages,
            from_language=source_language,
        )

        print("Original text:")
        print(text)

        print("\nTranslations:")

        for item in response:
            for translation in item.translations:
                print(
                    f"{translation.language}: "
                    f"{translation.text}"
                )

    except HttpResponseError as error:
        print("\nTranslation failed.")
        print(error)


if __name__ == "__main__":
    main()