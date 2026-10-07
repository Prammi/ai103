import os

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv


def main():
    # ---------------------------------------------------------
    # Clear console
    # ---------------------------------------------------------
    os.system("cls" if os.name == "nt" else "clear")

    # ---------------------------------------------------------
    # Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")

    if not speech_key:
        raise ValueError("SPEECH_KEY is not set in .env")

    if not speech_region:
        raise ValueError("SPEECH_REGION is not set in .env")

    # ---------------------------------------------------------
    # Configure Speech Translation
    # ---------------------------------------------------------
    translation_config = speechsdk.translation.SpeechTranslationConfig(
        subscription=speech_key,
        region=speech_region,
    )

    # Language that the user will SPEAK
    translation_config.speech_recognition_language = "en-US"

    # Languages that we want to translate INTO
    translation_config.add_target_language("hi")
    translation_config.add_target_language("fr")

    # ---------------------------------------------------------
    # Use default microphone
    # ---------------------------------------------------------
    audio_config = speechsdk.audio.AudioConfig(
        use_default_microphone=True
    )

    # ---------------------------------------------------------
    # Create Translation Recognizer
    # ---------------------------------------------------------
    translation_recognizer = speechsdk.translation.TranslationRecognizer(
        translation_config=translation_config,
        audio_config=audio_config,
    )

    # ---------------------------------------------------------
    # Listen and translate
    # ---------------------------------------------------------
    print("Speak something in English...")
    print("Example: Microsoft Foundry provides tools for building AI applications.")
    print()

    result = translation_recognizer.recognize_once_async().get()

    # ---------------------------------------------------------
    # Successful translation
    # ---------------------------------------------------------
    if result.reason == speechsdk.ResultReason.TranslatedSpeech:

        print("Recognized English:")
        print(result.text)

        print("\nTranslations:")

        for language, translated_text in result.translations.items():
            print(f"{language}: {translated_text}")

    # ---------------------------------------------------------
    # Speech was not recognized
    # ---------------------------------------------------------
    elif result.reason == speechsdk.ResultReason.NoMatch:

        print("No speech could be recognized.")

        print(
            f"Details: "
            f"{result.no_match_details}"
        )

    # ---------------------------------------------------------
    # Request failed / canceled
    # ---------------------------------------------------------
    elif result.reason == speechsdk.ResultReason.Canceled:

        cancellation_details = result.cancellation_details

        print("Speech translation was canceled.")
        print(
            f"Reason: "
            f"{cancellation_details.reason}"
        )

        if cancellation_details.error_details:
            print(
                f"Error details: "
                f"{cancellation_details.error_details}"
            )

    else:
        print(
            f"Unexpected result reason: "
            f"{result.reason}"
        )


if __name__ == "__main__":
    main()