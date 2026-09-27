import base64
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def encode_pdf(pdf_path: str) -> str:
    """
    Read a PDF file and convert it to a Base64 data URL.
    """

    with open(pdf_path, "rb") as pdf_file:
        encoded_pdf = base64.b64encode(
            pdf_file.read()
        ).decode("utf-8")

    return f"data:application/pdf;base64,{encoded_pdf}"


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
    # PDF
    # ---------------------------------------------------------
    pdf_path = "comparison_invoice.pdf"

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"Could not find PDF: {pdf_path}"
        )

    # ---------------------------------------------------------
    # Authenticate
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
    # Get OpenAI-compatible client
    # ---------------------------------------------------------
    client = project_client.get_openai_client()

    # ---------------------------------------------------------
    # Convert local PDF to Base64
    # ---------------------------------------------------------
    pdf_data = encode_pdf(pdf_path)

    print("\nSending the SAME invoice to the LLM...")
    print(f"Model: {model_name}")

    # ---------------------------------------------------------
    # Ask the LLM to extract exactly the same fields
    # ---------------------------------------------------------
    response = client.responses.create(
        model=model_name,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "comparison_invoice.pdf",
                        "file_data": pdf_data,
                    },
                    {
                        "type": "input_text",
                        "text": """
Extract the following information from the attached invoice.

Return ONLY valid JSON.

Required structure:

{
  "VendorName": "string",
  "InvoiceNumber": "string",
  "InvoiceDate": "YYYY-MM-DD",
  "DueDate": "YYYY-MM-DD",
  "PurchaseOrderNumber": "string",
  "PaymentTerms": "string",
  "Currency": "string",
  "TotalAmount": 0,
  "Items": [
    {
      "Description": "string",
      "Quantity": 0,
      "UnitPrice": 0,
      "Amount": 0
    }
  ]
}

Rules:
- Extract values only from the invoice.
- Do not invent missing values.
- Preserve numeric values accurately.
- TotalAmount must be a number.
- Quantity, UnitPrice and Amount must be numbers.
"""
                    },
                ],
            }
        ],
    )

    # ---------------------------------------------------------
    # Print LLM result
    # ---------------------------------------------------------
    print("\n")
    print("=" * 80)
    print("LLM RESULT")
    print("=" * 80)

    print(response.output_text)

    print("\n")
    print("=" * 80)
    print("LLM ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()