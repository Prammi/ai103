import os

import uvicorn
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from starlette.applications import Starlette

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)

from agent_framework.a2a import A2AExecutor
from agent_framework.foundry import FoundryChatClient


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")

HOST = "127.0.0.1"
PORT = 8002
AGENT_URL = f"http://{HOST}:{PORT}/"


if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT is missing from .env")

if not MODEL_DEPLOYMENT_NAME:
    raise ValueError("MODEL_DEPLOYMENT_NAME is missing from .env")


# =========================================================
# STEP 1: CREATE FOUNDRY CHAT CLIENT
# =========================================================

credential = AzureCliCredential()

foundry_client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model=MODEL_DEPLOYMENT_NAME,
    credential=credential,
)


# =========================================================
# STEP 2: CREATE SANDWICH AGENT
# =========================================================

sandwich_agent = foundry_client.as_agent(
    name="SandwichAgent",
    instructions=(
        "You are the Sandwich Specialist for a cafe. "
        "You handle sandwich and lunch-related requests. "
        "Help customers choose sandwiches and simple lunch options. "
        "You can suggest options such as grilled cheese, vegetable sandwich, "
        "paneer sandwich, club sandwich, and similar cafe lunch items. "
        "Keep your answers short and friendly."
    ),
)


# =========================================================
# STEP 3: DEFINE SANDWICH AGENT SKILL
# =========================================================

sandwich_skill = AgentSkill(
    id="sandwich-specialist",
    name="Sandwich Specialist",
    description=(
        "Handles sandwich and lunch-related requests and helps "
        "customers choose suitable cafe food options."
    ),
    tags=[
        "sandwich",
        "lunch",
        "food",
        "grilled cheese",
        "paneer",
    ],
    examples=[
        "I want a sandwich",
        "Suggest something for lunch",
        "Can I get a grilled cheese sandwich?",
    ],
)


# =========================================================
# STEP 4: CREATE PUBLIC A2A AGENT CARD
# =========================================================

sandwich_agent_card = AgentCard(
    name="Sandwich Agent",
    description=(
        "A remote cafe specialist that handles sandwiches "
        "and lunch-related requests."
    ),
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(
        streaming=True,
    ),
    supported_interfaces=[
        AgentInterface(
            url=AGENT_URL,
            protocol_binding="JSONRPC",
        ),
    ],
    skills=[
        sandwich_skill,
    ],
)


# =========================================================
# STEP 5: CREATE A2A EXECUTOR
# =========================================================

sandwich_executor = A2AExecutor(
    sandwich_agent,
    stream=True,
)


# =========================================================
# STEP 6: CREATE REQUEST HANDLER
# =========================================================

sandwich_request_handler = DefaultRequestHandler(
    agent_executor=sandwich_executor,
    task_store=InMemoryTaskStore(),
    agent_card=sandwich_agent_card,
)


# =========================================================
# STEP 7: CREATE A2A ROUTES
# =========================================================

routes = [
    *create_agent_card_routes(
        sandwich_agent_card,
    ),
    *create_jsonrpc_routes(
        sandwich_request_handler,
        "/",
    ),
]


# =========================================================
# STEP 8: CREATE STARLETTE SERVER
# =========================================================

app = Starlette(
    routes=routes,
)


# =========================================================
# STEP 9: START SERVER
# =========================================================

if __name__ == "__main__":

    print()
    print("==========================================")
    print("          SANDWICH AGENT SERVER")
    print("==========================================")
    print()
    print(f"Sandwich Agent : {AGENT_URL}")
    print(f"Model          : {MODEL_DEPLOYMENT_NAME}")
    print()
    print("Waiting for A2A requests...")
    print()

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )