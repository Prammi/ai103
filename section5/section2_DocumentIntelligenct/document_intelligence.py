import os
from pathlib import Path

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.contentunderstanding import ContentUnderstandingClient


load_dotenv()

endpoint = os.environ["CONTENT_UNDERSTANDING_ENDPOINT"]

pdf_path = Path(__file__).parent / "corporate_cost_analysis_report.pdf"

client = ContentUnderstandingClient(
    endpoint=endpoint,
    credential=DefaultAzureCredential(),
)

with open(pdf_path, "rb") as file:
    pdf_bytes = file.read()

print(f"Analyzing: {pdf_path.name}")

poller = client.begin_analyze_binary(
    analyzer_id="prebuilt-layout",
    binary_input=pdf_bytes,
    content_type="application/pdf",
)

result = poller.result()

print("\n" + "=" * 70)
print("EXTRACTED DOCUMENT CONTENT")
print("=" * 70)

for content in result.get("contents", []):
    # Document-level markdown/text
    markdown = content.get("markdown")

    if markdown:
        print("\n--- DOCUMENT TEXT ---")
        print(markdown)

    # Pages
    for page in content.get("pages", []):
        print(f"\n--- PAGE {page.get('pageNumber', '?')} ---")

        for line in page.get("lines", []):
            text = line.get("content")
            if text:
                print(text)

        # Tables
        for table in page.get("tables", []):
            print("\n[TABLE]")

            for row in table.get("cells", []):
                print(
                    f"Row={row.get('rowIndex')} "
                    f"Column={row.get('columnIndex')} "
                    f"Value={row.get('content')}"
                )

print("\n" + "=" * 70)
print("Extraction completed.")