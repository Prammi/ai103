import os
import json
from pathlib import Path

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentunderstanding import ContentUnderstandingClient
from openai import OpenAI


load_dotenv()

CONTENT_UNDERSTANDING_ENDPOINT = os.environ["CONTENT_UNDERSTANDING_ENDPOINT"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ["MODEL_DEPLOYMENT_NAME"]

pdf_path = Path(__file__).parent / "corporate_cost_analysis_report.pdf"


# ---------------------------------------------------------
# 1. Document Intelligence
# ---------------------------------------------------------

credential = DefaultAzureCredential()

cu_client = ContentUnderstandingClient(
    endpoint=CONTENT_UNDERSTANDING_ENDPOINT,
    credential=credential,
)

with open(pdf_path, "rb") as file:
    pdf_bytes = file.read()

print("Running Document Intelligence...")

poller = cu_client.begin_analyze_binary(
    analyzer_id="prebuilt-layout",
    binary_input=pdf_bytes,
    content_type="application/pdf",
)

result = poller.result()

contents = result.get("contents", [])

if not contents:
    raise RuntimeError("Document Intelligence returned no contents.")


# ---------------------------------------------------------
# 2. Extract the actual document content
# ---------------------------------------------------------

extracted_document = []

for content in contents:

    if content.get("markdown"):
        extracted_document.append(
            content["markdown"]
        )

    for page in content.get("pages", []):

        page_number = page.get("pageNumber")

        page_data = {
            "page": page_number,
            "lines": [],
            "tables": [],
        }

        for line in page.get("lines", []):
            text = line.get("content")

            if text:
                page_data["lines"].append(text)

        for table in page.get("tables", []):

            table_rows = {}

            for cell in table.get("cells", []):

                row_index = cell.get("rowIndex")
                column_index = cell.get("columnIndex")
                cell_content = cell.get("content", "")

                table_rows.setdefault(row_index, {})
                table_rows[row_index][column_index] = cell_content

            rows = []

            for row_index in sorted(table_rows):
                row = table_rows[row_index]

                rows.append([
                    row[column]
                    for column in sorted(row)
                ])

            page_data["tables"].append(rows)

        extracted_document.append(page_data)


# ---------------------------------------------------------
# 3. Convert extraction result to JSON
# ---------------------------------------------------------

document_for_llm = json.dumps(
    extracted_document,
    indent=2,
    ensure_ascii=False,
)


print("\nDocument extraction completed.")
print(f"Extracted content size: {len(document_for_llm)} characters")


# ---------------------------------------------------------
# 4. Create Azure OpenAI client
# ---------------------------------------------------------

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)

openai_client = OpenAI(
    base_url=f"{AZURE_OPENAI_ENDPOINT}/",
    api_key=token_provider,
)


# ---------------------------------------------------------
# 5. GPT reasons over Document Intelligence output
# ---------------------------------------------------------

prompt = f"""
You are analyzing a corporate cloud cost report.

The following information was extracted PROGRAMMATICALLY
from the PDF by Document Intelligence.

Do not assume information that is not present.

Analyze the extracted document and return:

1. Main cost drivers
2. Why the cost increased
3. A reasonable next-month cost estimate
4. The calculation used for the estimate
5. Assumptions and uncertainty

The estimate must clearly state whether it is a reliable
forecast or only a scenario-based estimate.

DOCUMENT INTELLIGENCE OUTPUT:

{document_for_llm}
"""


print("\nSending extracted document to GPT...")

response = openai_client.responses.create(
    model=MODEL_DEPLOYMENT_NAME,
    input=prompt,
)


# ---------------------------------------------------------
# 6. Display GPT result
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("GPT ANALYSIS OF DOCUMENT INTELLIGENCE OUTPUT")
print("=" * 70)

print(response.output_text)