import os

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def get_field_value(field):
    """
    Extract the actual value from a Content Understanding field
    based on its field type.
    """

    if field is None:
        return None

    if field.type == "string":
        return field.value_string

    if field.type == "number":
        return field.value_number

    if field.type == "date":
        return field.value_date

    return None


def main():
    # ---------------------------------------------------------
    # Load environment variables
    # ---------------------------------------------------------
    load_dotenv()

    endpoint = os.getenv("CONTENT_UNDERSTANDING_ENDPOINT")
    analyzer_id = os.getenv("CONTENT_UNDERSTANDING_ANALYZER_ID")

    if not endpoint:
        raise ValueError(
            "CONTENT_UNDERSTANDING_ENDPOINT is not configured in .env"
        )

    if not analyzer_id:
        raise ValueError(
            "CONTENT_UNDERSTANDING_ANALYZER_ID is not configured in .env"
        )

    # ---------------------------------------------------------
    # Invoice PDF
    # ---------------------------------------------------------
    pdf_path = "comparison_invoice.pdf"

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"Could not find PDF: {pdf_path}"
        )

    # ---------------------------------------------------------
    # Authenticate with Azure
    # ---------------------------------------------------------
    credential = DefaultAzureCredential()

    # ---------------------------------------------------------
    # Create Content Understanding client
    # ---------------------------------------------------------
    client = ContentUnderstandingClient(
        endpoint=endpoint,
        credential=credential,
    )

    # ---------------------------------------------------------
    # Read PDF
    # ---------------------------------------------------------
    with open(pdf_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()

    print("\nSending invoice to Content Understanding...")
    print(f"Analyzer: {analyzer_id}")

    # ---------------------------------------------------------
    # Send PDF to our analyzer
    # ---------------------------------------------------------
    poller = client.begin_analyze_binary(
        analyzer_id=analyzer_id,
        binary_input=pdf_bytes,
        content_type="application/pdf",
    )

    print("Waiting for analysis to complete...")

    result = poller.result()

    # ---------------------------------------------------------
    # Make sure a document was returned
    # ---------------------------------------------------------
    if not result.contents:
        raise ValueError(
            "Content Understanding returned no document content."
        )

    content = result.contents[0]
    fields = content.fields

    # ---------------------------------------------------------
    # Print main invoice fields
    # ---------------------------------------------------------
    print("\n")
    print("=" * 80)
    print("CONTENT UNDERSTANDING RESULT")
    print("=" * 80)

    field_names = [
        "VendorName",
        "InvoiceNumber",
        "InvoiceDate",
        "DueDate",
        "PurchaseOrderNumber",
        "PaymentTerms",
        "Currency",
        "TotalAmount",
    ]

    for field_name in field_names:
        field = fields.get(field_name)

        value = get_field_value(field)

        confidence = None

        if field is not None:
            confidence = field.confidence

        print(
            f"{field_name:<22}: "
            f"{str(value):<40} "
            f"Confidence: {confidence}"
        )

    # ---------------------------------------------------------
    # Print invoice line items
    # ---------------------------------------------------------
    print("\n")
    print("=" * 80)
    print("LINE ITEMS")
    print("=" * 80)

    items_field = fields.get("Items")

    if items_field and items_field.value_array:

        for index, item in enumerate(
            items_field.value_array,
            start=1,
        ):
            item_fields = item.value_object

            description = get_field_value(
                item_fields.get("Description")
            )

            quantity = get_field_value(
                item_fields.get("Quantity")
            )

            unit_price = get_field_value(
                item_fields.get("UnitPrice")
            )

            amount = get_field_value(
                item_fields.get("Amount")
            )

            print(f"\nItem {index}")
            print(f"  Description : {description}")
            print(f"  Quantity    : {quantity}")
            print(f"  Unit Price  : {unit_price}")
            print(f"  Amount      : {amount}")

    else:
        print("No line items were extracted.")

    print("\n")
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()