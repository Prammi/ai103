import base64
import json
import mimetypes
import os
from email import policy
from email.parser import BytesParser
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
MODEL = os.environ["MODEL_DEPLOYMENT_NAME"]

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)

client = OpenAI(
    base_url=f"{ENDPOINT}/",
    api_key=token_provider,
)

EMAILS_FOLDER = Path("emails")
ATTACHMENTS_FOLDER = Path("attachments")


def extract_email_content(email_path: Path) -> tuple[str, list[Path]]:
    """Read an .eml file and return the email body and attachment paths."""

    with email_path.open("rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    body = ""
    attachment_paths = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()

            if content_type == "text/plain" and disposition != "attachment":
                body = part.get_content()

            elif disposition == "attachment":
                filename = part.get_filename()

                if not filename:
                    continue

                attachment_path = ATTACHMENTS_FOLDER / filename

                if attachment_path.exists():
                    attachment_paths.append(attachment_path)

    else:
        body = message.get_content()

    return body.strip(), attachment_paths


def image_to_data_url(image_path: Path) -> str:
    """Convert an image to a base64 data URL."""

    mime_type, _ = mimetypes.guess_type(image_path.name)

    if not mime_type:
        mime_type = "image/png"

    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def analyze_incident(email_path: Path) -> dict:
    """Analyze email text and image evidence using GPT-5."""

    body, attachments = extract_email_content(email_path)

    content = [
        {
            "type": "input_text",
            "text": f"""
Analyze this corporate IT incident.

Use BOTH the email and the attached image.

Return ONLY valid JSON using this structure:

{{
    "employee": "",
    "department": "",
    "application_or_system": "",
    "category": "",
    "symptoms": [],
    "error_details": "",
    "severity": "",
    "business_impact": "",
    "evidence_from_attachment": "",
    "enrichment": {{
        "priority": "",
        "support_team": "",
        "search_terms": []
    }}
}}

Extract the following information:

- employee
- department
- application_or_system
- category
- symptoms
- error_details
- severity
- business_impact
- evidence_from_attachment

Then enrich the incident with:

- priority: Critical, High, Medium, or Low
- support_team: the most appropriate corporate IT support team
- search_terms: useful terms that could be used to find similar incidents

Important:
- Use information from BOTH the email and image.
- Do not invent technical root causes.
- Do not assume information that is not supported by the evidence.
- Return only valid JSON.

EMAIL:
{body}
""",
        }
    ]

    for attachment in attachments:
        content.append(
            {
                "type": "input_image",
                "image_url": image_to_data_url(attachment),
            }
        )

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "user",
                "content": content,
            }
        ],
    )

    return json.loads(response.output_text)


def main():
    email_files = sorted(EMAILS_FOLDER.glob("*.eml"))

    if not email_files:
        print("No .eml files found.")
        return

    for email_path in email_files:
        print("=" * 70)
        print(f"INCIDENT: {email_path.name}")
        print("=" * 70)

        try:
            result = analyze_incident(email_path)
            print(json.dumps(result, indent=2))

        except Exception as exc:
            print(f"ERROR: {exc}")

        print()


if __name__ == "__main__":
    main()