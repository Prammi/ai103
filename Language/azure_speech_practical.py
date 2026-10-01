import os
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


# ============================================================
# AI-103 SECTION 4.4
# CREATE SPEECH-ENABLED APPS WITH AZURE SPEECH
#
# This single practical demonstrates:
#
# 1. Speech-to-Text (STT) from an audio file
# 2. Speech-to-Text (STT) from microphone
# 3. Text-to-Speech (TTS)
# 4. Voice selection
# 5. Audio output format
# 6. SSML
#
# IMPORTANT:
#
# Section 4.3:
# Audio -> Generative AI speech model -> LLM -> speech model
#
# Section 4.4:
# Audio -> Azure Speech service -> Text
# Text  -> Azure Speech service -> Audio
# ============================================================


# ------------------------------------------------------------
# Load environment variables from .env
# ------------------------------------------------------------
load_dotenv()

SPEECH_ENDPOINT = os.getenv("LANGUAGE_ENDPOINT")


# ------------------------------------------------------------
# Files used by this practical
# ------------------------------------------------------------

# We already used this audio file in Section 4.3.
INPUT_AUDIO_FILE = "hyderabad_temperature_question.wav"

# Output from normal Text-to-Speech.
TTS_OUTPUT_FILE = "azure_speech_output.wav"

# Output from SSML Text-to-Speech.
SSML_OUTPUT_FILE = "azure_speech_ssml_output.wav"


# ============================================================
# 1. CREATE AZURE SPEECH CONFIGURATION
# ============================================================

def create_speech_config():
    """
    Create the common Azure Speech configuration.

    SpeechConfig tells the Speech SDK:

        - Which Azure AI resource should be used
        - How we authenticate

    We use:

        DefaultAzureCredential
                +
        Microsoft Entra authentication

    instead of storing an API key in our .env file.

    IMPORTANT AI-103 CONCEPT:

        Authentication = Who are you?

        RBAC = What are you allowed to do?
    """

    if not SPEECH_ENDPOINT:
        raise ValueError(
            "LANGUAGE_ENDPOINT is not set in the .env file."
        )

    credential = DefaultAzureCredential()

    speech_config = speechsdk.SpeechConfig(
        token_credential=credential,
        endpoint=SPEECH_ENDPOINT,
    )

    return speech_config


# ============================================================
# 2. SPEECH-TO-TEXT FROM AUDIO FILE
# ============================================================

def speech_to_text_from_file():
    """
    Convert speech stored in an audio file into text.

    FLOW:

        WAV audio
            ↓
        Azure Speech
            ↓
        Speech-to-Text
            ↓
        Text

    Example:

        "What is the current temperature in Hyderabad?"

    IMPORTANT:

    Azure Speech is TRANSCRIBING here.

    It is NOT reasoning about what the question means.
    """

    print("\n--- SPEECH TO TEXT: AUDIO FILE ---")

    audio_path = Path(INPUT_AUDIO_FILE)

    if not audio_path.exists():
        print(f"Audio file not found: {audio_path.resolve()}")
        return

    speech_config = create_speech_config()

    # Language spoken in the audio.
    speech_config.speech_recognition_language = "en-US"

    # Tell the Speech SDK where the audio comes from.
    audio_config = speechsdk.audio.AudioConfig(
        filename=str(audio_path)
    )

    # SpeechRecognizer performs Speech-to-Text.
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    print("Transcribing audio...")

    result = speech_recognizer.recognize_once_async().get()

    # --------------------------------------------------------
    # Check recognition result
    # --------------------------------------------------------

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:

        print("\nRecognized text:")
        print(result.text)

    elif result.reason == speechsdk.ResultReason.NoMatch:

        print("\nSpeech could not be recognized.")

    elif result.reason == speechsdk.ResultReason.Canceled:

        cancellation = result.cancellation_details

        print("\nSpeech recognition was canceled.")
        print("Reason:", cancellation.reason)

        if cancellation.error_details:
            print("Error:", cancellation.error_details)


# ============================================================
# 3. SPEECH-TO-TEXT FROM MICROPHONE
# ============================================================

def speech_to_text_from_microphone():
    """
    Listen through the computer microphone and convert
    the user's speech into text.

    FLOW:

        Microphone
            ↓
        Azure Speech
            ↓
        Speech-to-Text
            ↓
        Text

    recognize_once_async() listens for one utterance.

    Later in Section 4.6 we will learn about more
    conversational / real-time voice experiences.
    """

    print("\n--- SPEECH TO TEXT: MICROPHONE ---")

    speech_config = create_speech_config()

    speech_config.speech_recognition_language = "en-US"

    # Use the computer's default microphone.
    audio_config = speechsdk.audio.AudioConfig(
        use_default_microphone=True
    )

    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    print("\nSpeak into your microphone...")

    result = speech_recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:

        print("\nYou said:")
        print(result.text)

    elif result.reason == speechsdk.ResultReason.NoMatch:

        print("\nSpeech could not be recognized.")

    elif result.reason == speechsdk.ResultReason.Canceled:

        cancellation = result.cancellation_details

        print("\nSpeech recognition was canceled.")
        print("Reason:", cancellation.reason)

        if cancellation.error_details:
            print("Error:", cancellation.error_details)


# ============================================================
# 4. TEXT-TO-SPEECH
# ============================================================

def text_to_speech():
    """
    Convert normal text into spoken audio.

    FLOW:

        Text
          ↓
        Azure Speech
          ↓
        Text-to-Speech
          ↓
        Audio file

    This demonstrates THREE important AI-103 concepts:

        1. Speech synthesis
        2. Voice selection
        3. Audio output format
    """

    print("\n--- TEXT TO SPEECH ---")

    speech_config = create_speech_config()

    # --------------------------------------------------------
    # VOICE SELECTION
    # --------------------------------------------------------
    #
    # Voice determines WHO / HOW the speech sounds.
    #
    # Do NOT confuse this with audio format.
    #
    # Voice = speaker
    # Format = encoding / technical audio representation
    # --------------------------------------------------------

    speech_config.speech_synthesis_voice_name = (
        "en-US-AvaMultilingualNeural"
    )

    # --------------------------------------------------------
    # AUDIO OUTPUT FORMAT
    # --------------------------------------------------------
    #
    # This determines how the audio is encoded.
    #
    # Here we request:
    #
    # RIFF/WAV
    # 24 kHz
    # 16-bit
    # mono PCM
    #
    # AI-103:
    #
    # Change speaker       -> Voice
    # Change encoding      -> Output format
    # Change rate/pitch    -> SSML
    # --------------------------------------------------------

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )

    # Save synthesized speech to a WAV file.
    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=TTS_OUTPUT_FILE
    )

    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    text = (
        "Hello Pramod. "
        "This audio was generated using Azure Speech "
        "text to speech."
    )

    print("\nText:")
    print(text)

    print("\nGenerating speech...")

    result = speech_synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:

        print("\nSpeech generated successfully.")
        print(
            "Audio file:",
            Path(TTS_OUTPUT_FILE).resolve()
        )

    elif result.reason == speechsdk.ResultReason.Canceled:

        cancellation = result.cancellation_details

        print("\nSpeech synthesis was canceled.")
        print("Reason:", cancellation.reason)

        if cancellation.error_details:
            print("Error:", cancellation.error_details)


# ============================================================
# 5. TEXT-TO-SPEECH USING SSML
# ============================================================

def text_to_speech_with_ssml():
    """
    Generate speech using SSML.

    SSML =
        Speech Synthesis Markup Language

    SSML gives us finer control over HOW speech sounds.

    Examples:

        - Voice
        - Speaking rate
        - Pitch
        - Volume
        - Pauses
        - Pronunciation
        - Emphasis

    IMPORTANT AI-103 CLUE:

        "Control pronunciation, pauses, pitch,
         rate or speaking style"

                    ↓

                   SSML
    """

    print("\n--- TEXT TO SPEECH WITH SSML ---")

    speech_config = create_speech_config()

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=SSML_OUTPUT_FILE
    )

    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    # --------------------------------------------------------
    # SSML DOCUMENT
    # --------------------------------------------------------
    #
    # <voice>
    #     Select the voice.
    #
    # <prosody>
    #     Control rate, pitch, volume, etc.
    #
    # <break>
    #     Insert a pause.
    #
    # Here:
    #
    # rate="+10%"
    #     Speak slightly faster.
    #
    # pitch="+5%"
    #     Slightly increase pitch.
    #
    # break time="800ms"
    #     Pause for 800 milliseconds.
    # --------------------------------------------------------

    ssml = """
    <speak version="1.0"
           xmlns="http://www.w3.org/2001/10/synthesis"
           xml:lang="en-US">

        <voice name="en-US-AvaMultilingualNeural">

            <prosody rate="+10%" pitch="+5%">

                Welcome to the Azure Speech practical.

                <break time="800ms"/>

                This sentence is spoken after a short pause.

            </prosody>

        </voice>

    </speak>
    """

    print("\nGenerating speech using SSML...")

    result = speech_synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:

        print("\nSSML speech generated successfully.")
        print(
            "Audio file:",
            Path(SSML_OUTPUT_FILE).resolve()
        )

    elif result.reason == speechsdk.ResultReason.Canceled:

        cancellation = result.cancellation_details

        print("\nSSML synthesis was canceled.")
        print("Reason:", cancellation.reason)

        if cancellation.error_details:
            print("Error:", cancellation.error_details)


# ============================================================
# 6. MENU
# ============================================================

def show_menu():
    """
    Run each part independently.

    This makes it easier to understand what each
    Azure Speech capability is doing.
    """

    while True:

        print("\n")
        print("=" * 60)
        print("AI-103 - SECTION 4.4 - AZURE SPEECH PRACTICAL")
        print("=" * 60)

        print("1 - Speech-to-Text from audio file")
        print("2 - Speech-to-Text from microphone")
        print("3 - Text-to-Speech + voice + audio format")
        print("4 - Text-to-Speech using SSML")
        print("5 - Run file STT + TTS + SSML")
        print("0 - Exit")

        choice = input("\nSelect an option: ").strip()

        if choice == "1":

            speech_to_text_from_file()

        elif choice == "2":

            speech_to_text_from_microphone()

        elif choice == "3":

            text_to_speech()

        elif choice == "4":

            text_to_speech_with_ssml()

        elif choice == "5":

            print("\nRunning complete file-based practical...")

            speech_to_text_from_file()
            text_to_speech()
            text_to_speech_with_ssml()

        elif choice == "0":

            print("\nExiting.")
            break

        else:

            print("\nInvalid option. Please select 0-5.")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    show_menu()