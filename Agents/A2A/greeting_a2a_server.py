import os

import uvicorn
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

from agent_framework.a2a import A2AExecutor
from agent_framework.foundry import FoundryChatClient

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from starlette.applications import Starlette
from starlette.routing import Mount


# =========================================================
# PART 1 - SETTINGS
# =========================================================

load_dotenv()

FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
FOUNDRY_MODEL = os.getenv("FOUNDRY_MODEL")

HOST = "127.0.0.1"
PORT = 8000

GREETING_URL = f"http://{HOST}:{PORT}/greeting/"
SUPPORT_URL = f"http://{HOST}:{PORT}/support/"

if not FOUNDRY_PROJECT_ENDPOINT:
    raise ValueError("FOUNDRY_PROJECT_ENDPOINT is missing from .env")

if not FOUNDRY_MODEL:
    raise ValueError("FOUNDRY_MODEL is missing from .env")


# =========================================================
# PART 2 - ONE FOUNDRY CLIENT
# Both non-persistent Agent Framework agents can use the
# same Foundry model client.
# =========================================================

credential = AzureCliCredential()

foundry_client = FoundryChatClient(
    project_endpoint=FOUNDRY_PROJECT_ENDPOINT,
    model=FOUNDRY_MODEL,
    credential=credential,
)


# =========================================================
# PART 3 - AGENT 1: GREETING AGENT
# =========================================================

greeting_agent = foundry_client.as_agent(
    name="GreetingAgent",
    description="An agent that provides short friendly greetings.",
    instructions=(
        "You are a greeting agent. "
        "Give short and friendly greetings. "
        "Keep your response to one sentence."
    ),
)


greeting_skill = AgentSkill(
    id="greeting",
    name="Greeting",
    description="Provides short friendly greetings.",
    tags=["greeting", "hello"],
    examples=["Good morning", "Say hello"],
)


greeting_card = AgentCard(
    name="Greeting Agent",
    description="A remote A2A agent that provides greetings.",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            url=GREETING_URL,
            protocol_binding="JSONRPC",
        )
    ],
    skills=[greeting_skill],
)


greeting_executor = A2AExecutor(
    greeting_agent,
    stream=True,
)


greeting_handler = DefaultRequestHandler(
    agent_executor=greeting_executor,
    task_store=InMemoryTaskStore(),
    agent_card=greeting_card,
)


# =========================================================
# PART 4 - AGENT 2: SUPPORT AGENT
# =========================================================

support_agent = foundry_client.as_agent(
    name="SupportAgent",
    description="An agent that provides short IT support guidance.",
    instructions=(
        "You are an IT support agent. "
        "Give short and practical IT support guidance. "
        "Keep your response to two short sentences."
    ),
)


support_skill = AgentSkill(
    id="it_support",
    name="IT Support",
    description="Provides basic IT support guidance.",
    tags=["support", "it", "help"],
    examples=["My VPN is not connecting", "I cannot sign in"],
)


support_card = AgentCard(
    name="Support Agent",
    description="A remote A2A agent that provides IT support guidance.",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            url=SUPPORT_URL,
            protocol_binding="JSONRPC",
        )
    ],
    skills=[support_skill],
)


support_executor = A2AExecutor(
    support_agent,
    stream=True,
)


support_handler = DefaultRequestHandler(
    agent_executor=support_executor,
    task_store=InMemoryTaskStore(),
    agent_card=support_card,
)


# =========================================================
# PART 5 - BUILD A SMALL A2A APP FOR EACH AGENT
#
# Each agent gets:
#   Agent Card routes  -> discovery
#   JSON-RPC routes    -> actual A2A communication
# =========================================================

greeting_app = Starlette(
    routes=[
        *create_agent_card_routes(greeting_card),
        *create_jsonrpc_routes(greeting_handler, "/"),
    ]
)


support_app = Starlette(
    routes=[
        *create_agent_card_routes(support_card),
        *create_jsonrpc_routes(support_handler, "/"),
    ]
)


# =========================================================
# PART 6 - MAIN SERVER ROUTING
#
# /greeting/... -> Greeting A2A application
# /support/...  -> Support A2A application
# =========================================================

app = Starlette(
    routes=[
        Mount("/greeting", app=greeting_app),
        Mount("/support", app=support_app),
    ]
)


# =========================================================
# PART 7 - START SERVER
# =========================================================

if __name__ == "__main__":
    print()
    print("==========================================")
    print("       TWO AGENT A2A SERVER")
    print("==========================================")
    print()
    print(f"Foundry Model  : {FOUNDRY_MODEL}")
    print(f"Greeting Agent : {GREETING_URL}")
    print(f"Support Agent  : {SUPPORT_URL}")
    print("Protocol       : JSON-RPC")
    print()
    print("Waiting for A2A requests...")
    print()

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )
