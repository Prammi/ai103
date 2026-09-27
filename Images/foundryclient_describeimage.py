import base64
import mimetypes
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


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
    # Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_name = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint:
        raise ValueError(
            "PROJECT_ENDPOINT is not configured in .env"
        )

    if not model_name:
        raise ValueError(
            "MODEL_DEPLOYMENT_NAME is not configured in .env"
        )

    # ---------------------------------------------------------
    # Authenticate with Azure
    # ---------------------------------------------------------
    credential = DefaultAzureCredential()

    # ---------------------------------------------------------
    # Create Foundry project client
    # ---------------------------------------------------------
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential,
    )

    # ---------------------------------------------------------
    # Get OpenAI-compatible client from Foundry
    # ---------------------------------------------------------
    client = project_client.get_openai_client()

    # ---------------------------------------------------------
    # Load local image
    # ---------------------------------------------------------
    image_path = "factory.jpg"

    if not os.path.exists(image_path):
        raise FileNotFoundError(
            f"Could not find image: {image_path}"
        )

    image_data = encode_image(image_path)

    # ---------------------------------------------------------
    # Send text + image to multimodal model
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
    # Display result
    # ---------------------------------------------------------
    print("\n--- MODEL RESPONSE ---\n")
    print(response.output_text)


if __name__ == "__main__":
    main()