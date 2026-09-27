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
PORT = 8001
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
# STEP 2: CREATE COFFEE AGENT
# =========================================================

coffee_agent = foundry_client.as_agent(
    name="CoffeeAgent",
    instructions=(
        "You are the Coffee Specialist for a cafe. "
        "You handle coffee-related requests. "
        "Help customers choose coffee drinks such as espresso, "
        "americano, cappuccino, latte, mocha, and similar drinks. "
        "Keep your answers short and friendly."
    ),
)


# =========================================================
# STEP 3: DEFINE COFFEE AGENT SKILL
# =========================================================

coffee_skill = AgentSkill(
    id="coffee-specialist",
    name="Coffee Specialist",
    description=(
        "Handles coffee-related requests and helps customers "
        "choose coffee drinks."
    ),
    tags=[
        "coffee",
        "espresso",
        "latte",
        "cappuccino",
        "drinks",
    ],
    examples=[
        "I want a cappuccino",
        "Suggest a coffee",
        "Can I get an espresso?",
    ],
)


# =========================================================
# STEP 4: CREATE PUBLIC A2A AGENT CARD
# =========================================================

coffee_agent_card = AgentCard(
    name="Coffee Agent",
    description=(
        "A remote cafe specialist that handles coffee "
        "and coffee-related requests."
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
        coffee_skill,
    ],
)


# =========================================================
# STEP 5: CREATE A2A EXECUTOR
# =========================================================

coffee_executor = A2AExecutor(
    coffee_agent,
    stream=True,
)


# =========================================================
# STEP 6: CREATE REQUEST HANDLER
# =========================================================

coffee_request_handler = DefaultRequestHandler(
    agent_executor=coffee_executor,
    task_store=InMemoryTaskStore(),
    agent_card=coffee_agent_card,
)


# =========================================================
# STEP 7: CREATE A2A ROUTES
# =========================================================

routes = [
    *create_agent_card_routes(
        coffee_agent_card,
    ),
    *create_jsonrpc_routes(
        coffee_request_handler,
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
    print("           COFFEE AGENT SERVER")
    print("==========================================")
    print()
    print(f"Coffee Agent : {AGENT_URL}")
    print(f"Model        : {MODEL_DEPLOYMENT_NAME}")
    print()
    print("Waiting for A2A requests...")
    print()

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )