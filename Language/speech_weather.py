import json
import os
from pathlib import Path

import requests
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------
INPUT_AUDIO_FILE = "hyderabad_temperature_question.wav"
OUTPUT_AUDIO_FILE = "weather_answer.mp3"

DEFAULT_QUESTION = "What is the current temperature in Hyderabad?"

DEFAULT_TTS_TEXT = (
    "Hello. This is a test of the text to speech model."
)


# ---------------------------------------------------------
# Load configuration
# ---------------------------------------------------------
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")
TRANSCRIBE_MODEL_DEPLOYMENT_NAME = os.getenv(
    "TRANSCRIBE_MODEL_DEPLOYMENT_NAME"
)
TTS_MODEL_DEPLOYMENT_NAME = os.getenv(
    "TTS_MODEL_DEPLOYMENT_NAME"
)


def validate_configuration():
    required_values = {
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "MODEL_DEPLOYMENT_NAME": MODEL_DEPLOYMENT_NAME,
        "TRANSCRIBE_MODEL_DEPLOYMENT_NAME":
            TRANSCRIBE_MODEL_DEPLOYMENT_NAME,
        "TTS_MODEL_DEPLOYMENT_NAME": TTS_MODEL_DEPLOYMENT_NAME,
    }

    missing = [
        name
        for name, value in required_values.items()
        if not value
    ]

    if missing:
        raise ValueError(
            "Missing .env values: " + ", ".join(missing)
        )


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------
def create_token_provider():
    return get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://ai.azure.com/.default",
    )


# ---------------------------------------------------------
# Client used by GPT-5 Responses API
# ---------------------------------------------------------
def create_responses_client():
    endpoint = AZURE_OPENAI_ENDPOINT.rstrip("/")

    return OpenAI(
        base_url=f"{endpoint}/openai/v1/",
        api_key=create_token_provider(),
    )


# ---------------------------------------------------------
# Client used by Audio APIs
# ---------------------------------------------------------
def create_audio_client():
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=create_token_provider(),
        api_version="2025-04-01-preview",
    )


# =========================================================
# STEP 1
# Speech → Text
# =========================================================
def transcribe_audio(audio_file_path):
    print("\n--- STEP 1: SPEECH TO TEXT ---")

    if not Path(audio_file_path).exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_file_path}"
        )

    client = create_audio_client()

    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL_DEPLOYMENT_NAME,
            file=audio_file,
        )

    text = transcription.text

    print("\nTranscription:")
    print(text)

    return text


# =========================================================
# WEATHER TOOL
# =========================================================
def get_current_weather(city):
    print(f"\n[TOOL CALLED] get_current_weather('{city}')")

    # -----------------------------------------------------
    # 1. Convert city → latitude / longitude
    # -----------------------------------------------------
    geocoding_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
    )

    geocoding_response = requests.get(
        geocoding_url,
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=20,
    )

    geocoding_response.raise_for_status()

    geocoding_data = geocoding_response.json()

    results = geocoding_data.get("results")

    if not results:
        return {
            "error": f"Could not find city: {city}"
        }

    location = results[0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    resolved_city = location["name"]
    country = location.get("country", "")

    # -----------------------------------------------------
    # 2. Get current weather
    # -----------------------------------------------------
    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    weather_response = requests.get(
        weather_url,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m",
            "timezone": "auto",
        },
        timeout=20,
    )

    weather_response.raise_for_status()

    weather_data = weather_response.json()

    current = weather_data["current"]
    units = weather_data["current_units"]

    result = {
        "city": resolved_city,
        "country": country,
        "temperature": current["temperature_2m"],
        "unit": units["temperature_2m"],
        "observation_time": current["time"],
    }

    print("\nWeather API result:")
    print(json.dumps(result, indent=2))

    return result


# =========================================================
# STEP 2
# GPT-5 → Tool → GPT-5
# =========================================================
def answer_weather_question(question):
    print("\n--- STEP 2: GPT-5 + WEATHER TOOL ---")

    print("\nQuestion:")
    print(question)

    client = create_responses_client()

    weather_tool = {
        "type": "function",
        "name": "get_current_weather",
        "description": (
            "Get the current temperature for a city. "
            "Use this tool whenever the user asks for "
            "current temperature or current weather."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": (
                        "City name, for example Hyderabad"
                    ),
                }
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    }

    # -----------------------------------------------------
    # Ask GPT-5
    # -----------------------------------------------------
    response = client.responses.create(
        model=MODEL_DEPLOYMENT_NAME,
        instructions=(
            "You are a weather assistant. "
            "For current weather information, always use "
            "the provided weather tool. "
            "Never invent current weather data."
        ),
        tools=[weather_tool],
        input=question,
    )

    tool_outputs = []

    # -----------------------------------------------------
    # Check whether GPT-5 requested our tool
    # -----------------------------------------------------
    for item in response.output:
        if (
            item.type == "function_call"
            and item.name == "get_current_weather"
        ):
            arguments = json.loads(item.arguments)

            city = arguments["city"]

            weather_result = get_current_weather(city)

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(weather_result),
                }
            )

    # -----------------------------------------------------
    # GPT-5 should have called the tool
    # -----------------------------------------------------
    if not tool_outputs:
        final_text = response.output_text

        print("\nGPT-5 response:")
        print(final_text)

        return final_text

    # -----------------------------------------------------
    # Give tool result back to GPT-5
    # -----------------------------------------------------
    final_response = client.responses.create(
        model=MODEL_DEPLOYMENT_NAME,
        previous_response_id=response.id,
        tools=[weather_tool],
        input=tool_outputs,
    )

    final_text = final_response.output_text

    print("\nFinal GPT-5 answer:")
    print(final_text)

    return final_text


# =========================================================
# STEP 3
# Text → Speech
# =========================================================
def text_to_speech(text):
    print("\n--- STEP 3: TEXT TO SPEECH ---")

    print("\nText being converted to speech:")
    print(text)

    client = create_audio_client()

    response = client.audio.speech.create(
        model=TTS_MODEL_DEPLOYMENT_NAME,
        voice="alloy",
        input=text,
        response_format="mp3",
    )

    response.write_to_file(OUTPUT_AUDIO_FILE)

    print("\nAudio created:")
    print(OUTPUT_AUDIO_FILE)

    return OUTPUT_AUDIO_FILE


# =========================================================
# OPTION 4
# Complete Pipeline
# =========================================================
def run_complete_pipeline():
    print("\n======================================")
    print("COMPLETE SPEECH WEATHER PIPELINE")
    print("======================================")

    # Step 1
    question = transcribe_audio(INPUT_AUDIO_FILE)

    # Step 2
    answer = answer_weather_question(question)

    # Step 3
    output_file = text_to_speech(answer)

    print("\n======================================")
    print("PIPELINE COMPLETE")
    print("======================================")

    print("\nFlow:")
    print("Audio")
    print("  ↓")
    print("Speech-to-Text")
    print("  ↓")
    print("GPT-5")
    print("  ↓")
    print("Weather Tool")
    print("  ↓")
    print("GPT-5")
    print("  ↓")
    print("Text-to-Speech")

    print(f"\nFinal audio: {output_file}")


# =========================================================
# Menu
# =========================================================
def show_menu():
    print("\n======================================")
    print("AI-103 - Speech Weather Practical")
    print("======================================")

    print("1 - Test Speech-to-Text")
    print("2 - Test GPT-5 + Weather Tool")
    print("3 - Test Text-to-Speech")
    print("4 - Run Complete Pipeline")
    print("0 - Exit")


def main():
    os.system("cls" if os.name == "nt" else "clear")

    validate_configuration()

    while True:
        show_menu()

        choice = input("\nSelect option: ").strip()

        try:
            if choice == "1":
                transcribe_audio(
                    INPUT_AUDIO_FILE
                )

            elif choice == "2":
                answer_weather_question(
                    DEFAULT_QUESTION
                )

            elif choice == "3":
                text_to_speech(
                    DEFAULT_TTS_TEXT
                )

            elif choice == "4":
                run_complete_pipeline()

            elif choice == "0":
                print("\nExiting.")
                break

            else:
                print(
                    "\nInvalid option. "
                    "Choose 0, 1, 2, 3, or 4."
                )

        except Exception as ex:
            print("\nERROR:")
            print(ex)

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()