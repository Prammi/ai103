
import base64
import mimetypes
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI


def encode_image(image_path: str) -> str:
    """
    Convert a local image into a Base64 data URI.
    """

    mime_type, _ = mimetypes.guess_type(image_path)

    if mime_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }:
        raise ValueError(
            "Unsupported image type. Use JPEG, PNG, WebP, or GIF."
        )

    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(
            image_file.read()
        ).decode("utf-8")

    return f"data:{mime_type};base64,{encoded_image}"


def main():
    # ---------------------------------------------------------
    # 1. Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    model_name = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not azure_openai_endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT is not configured in .env"
        )

    if not model_name:
        raise ValueError(
            "MODEL_DEPLOYMENT_NAME is not configured in .env"
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
    # 3. Create OpenAI client pointing to Azure OpenAI
    # ---------------------------------------------------------
    client = OpenAI(
        base_url=f"{azure_openai_endpoint.rstrip('/')}/openai/v1/",
        api_key=token_provider,
    )

    # ---------------------------------------------------------
    # 4. Load local image
    # ---------------------------------------------------------
    image_path = "factory.jpg"

    if not os.path.exists(image_path):
        raise FileNotFoundError(
            f"Could not find image: {image_path}"
        )

    # Convert the image to Base64 so it can be sent
    # inside the API request.
    image_data = encode_image(image_path)

    # ---------------------------------------------------------
    # 5. Send text + image to the multimodal model
    # ---------------------------------------------------------
    response = client.responses.create(
        model=model_name,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Describe this image. "
                            "Also identify any visible safety concerns."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": image_data,
                        "detail": "auto",
                    },
                ],
            }
        ],
    )

    # ---------------------------------------------------------
    # 6. Display model response
    # ---------------------------------------------------------
    print("\n--- MODEL RESPONSE ---\n")
    print(response.output_text)


if __name__ == "__main__":
    main()
