import base64
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI


def main():
    # ---------------------------------------------------------
    # 1. Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    image_model = os.getenv("IMAGE_MODEL_DEPLOYMENT_NAME")

    if not azure_openai_endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT is not configured in .env"
        )

    if not image_model:
        raise ValueError(
            "IMAGE_MODEL_DEPLOYMENT_NAME is not configured in .env"
        )

    # ---------------------------------------------------------
    # 2. Authenticate with Microsoft Entra ID
    # ---------------------------------------------------------
    credential = DefaultAzureCredential()

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    # ---------------------------------------------------------
    # 3. Create OpenAI client using Azure OpenAI endpoint
    # ---------------------------------------------------------
    client = OpenAI(
        base_url=f"{azure_openai_endpoint.rstrip('/')}/openai/v1/",
        api_key=token_provider,
    )

    # ---------------------------------------------------------
    # 4. Generate image
    # ---------------------------------------------------------
    print("Generating image...")

    result = client.images.generate(
        model=image_model,
        prompt=(
            "A modern semiconductor manufacturing clean room. "
            "Robotic equipment is processing silicon wafers. "
            "Engineers are wearing clean-room protective suits. "
            "Realistic professional photography."
        ),
        size="1024x1024",
        quality="medium",
        n=1,
    )

    # ---------------------------------------------------------
    # 5. Get Base64 image returned by the model
    # ---------------------------------------------------------
    image_base64 = result.data[0].b64_json

    if not image_base64:
        raise ValueError(
            "The model did not return Base64 image data."
        )

    # ---------------------------------------------------------
    # 6. Decode Base64 into image bytes
    # ---------------------------------------------------------
    image_bytes = base64.b64decode(image_base64)

    # ---------------------------------------------------------
    # 7. Save generated image
    # ---------------------------------------------------------
    output_file = "generated_image.png"

    with open(output_file, "wb") as file:
        file.write(image_bytes)

    print(f"Image successfully saved as: {output_file}")


if __name__ == "__main__":
    main()