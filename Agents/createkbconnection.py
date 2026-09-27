import os

import requests
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv


def load_configuration():
    """Load configuration from .env."""

    load_dotenv()

    project_resource_id = os.getenv("PROJECT_RESOURCE_ID")
    search_service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    knowledge_base_name = os.getenv("KNOWLEDGE_BASE_NAME")
    connection_name = os.getenv(
        "KB_CONNECTION_NAME",
        "support-policy-kb-connection",
    )

    required_values = {
        "PROJECT_RESOURCE_ID": project_resource_id,
        "SEARCH_SERVICE_ENDPOINT": search_service_endpoint,
        "KNOWLEDGE_BASE_NAME": knowledge_base_name,
    }

    for name, value in required_values.items():
        if not value:
            raise ValueError(f"{name} is not set in .env")

    return (
        project_resource_id.rstrip("/"),
        search_service_endpoint.rstrip("/"),
        knowledge_base_name,
        connection_name,
    )


def create_project_connection(
    project_resource_id,
    search_service_endpoint,
    knowledge_base_name,
    connection_name,
):
    """Create the Foundry RemoteTool connection."""

    credential = DefaultAzureCredential()

    # Token used to call Azure Resource Manager.
    bearer_token_provider = get_bearer_token_provider(
        credential,
        "https://management.azure.com/.default",
    )

    token = bearer_token_provider()

    # Knowledge Base MCP endpoint.
    mcp_endpoint = (
        f"{search_service_endpoint}"
        f"/knowledgebases/{knowledge_base_name}/mcp"
        f"?api-version=2026-08-01-preview"
    )

    # Azure Resource Manager endpoint used to create the
    # Foundry project connection.
    connection_url = (
        f"https://management.azure.com"
        f"{project_resource_id}"
        f"/connections/{connection_name}"
        f"?api-version=2025-10-01-preview"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    body = {
        "name": connection_name,
        "type": "Microsoft.MachineLearningServices/workspaces/connections",
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": mcp_endpoint,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {
                "ApiType": "Azure",
            },
        },
    }

    print("\nCreating Foundry project connection...")
    print(f"Connection name : {connection_name}")
    print(f"Knowledge Base  : {knowledge_base_name}")
    print(f"MCP endpoint    : {mcp_endpoint}")

    response = requests.put(
        connection_url,
        headers=headers,
        json=body,
        timeout=60,
    )

    if not response.ok:
        print("\nConnection creation failed.")
        print(f"HTTP Status: {response.status_code}")
        print(response.text)
        response.raise_for_status()

    print("\nConnection created successfully.")

    result = response.json()

    print(f"Name     : {result.get('name')}")
    print(
        "Auth type:",
        result.get("properties", {}).get("authType"),
    )
    print(
        "Category :",
        result.get("properties", {}).get("category"),
    )
    print(
        "Target   :",
        result.get("properties", {}).get("target"),
    )


def main():
    print("\n=== CREATE KNOWLEDGE BASE CONNECTION ===")

    (
        project_resource_id,
        search_service_endpoint,
        knowledge_base_name,
        connection_name,
    ) = load_configuration()

    create_project_connection(
        project_resource_id=project_resource_id,
        search_service_endpoint=search_service_endpoint,
        knowledge_base_name=knowledge_base_name,
        connection_name=connection_name,
    )


if __name__ == "__main__":
    main()