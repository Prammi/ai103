import re

import uvicorn
from starlette.applications import Starlette

from a2a.helpers import new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Part,
    TaskState,
)


# =========================================================
# CONFIGURATION
# =========================================================

HOST = "127.0.0.1"
PORT = 8003
AGENT_URL = f"http://{HOST}:{PORT}/"


# =========================================================
# STEP 1: HELPER TO READ TEXT FROM INCOMING MESSAGE
# =========================================================

def get_message_text(context: RequestContext) -> str:
    if context.message is None:
        return ""

    text_parts = []

    for part in context.message.parts:
        if part.root.text:
            text_parts.append(part.root.text)

    return " ".join(text_parts).strip()


# =========================================================
# STEP 2: CATERING A2A EXECUTOR
#
# Unlike Coffee/Sandwich, we control the Task lifecycle
# ourselves so we can demonstrate:
#
# working
#    ↓
# input-required
#    ↓
# working
#    ↓
# completed + artifact
# =========================================================

class CateringAgentExecutor(AgentExecutor):

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        if context.message is None:
            raise ValueError("A2A message is required.")

        if context.context_id is None:
            raise ValueError("A2A context ID is required.")

        # -------------------------------------------------
        # Is this a NEW task or an EXISTING task?
        # -------------------------------------------------

        task = context.current_task

        if task is None:

            # NEW catering request
            task = new_task_from_user_message(context.message)

            await event_queue.enqueue_event(task)

        # -------------------------------------------------
        # TaskUpdater manages A2A task state
        # -------------------------------------------------

        updater = TaskUpdater(
            event_queue,
            task.id,
            context.context_id,
        )

        await updater.start_work()

        # -------------------------------------------------
        # Read incoming user/caller message
        # -------------------------------------------------

        message_text = get_message_text(context)

        print()
        print("------------------------------------------")
        print("CATERING AGENT RECEIVED MESSAGE")
        print("------------------------------------------")
        print(f"Task ID : {task.id}")
        print(f"Message : {message_text}")
        print()

        # -------------------------------------------------
        # Try to find number of people in the message
        #
        # Example:
        # "Prepare lunch for 20 people"
        # "20 people"
        # -------------------------------------------------

        number_match = re.search(
            r"\b(\d+)\b",
            message_text,
        )

        # =================================================
        # CASE 1:
        # Number of people is NOT known.
        #
        # Catering Agent cannot complete the task.
        # =================================================

        if number_match is None:

            print("Number of people is missing.")
            print("Task status -> INPUT_REQUIRED")
            print()

            await updater.update_status(
                state=TaskState.TASK_STATE_INPUT_REQUIRED,
                message=updater.new_agent_message(
                    [
                        Part(
                            text=(
                                "How many people should I prepare "
                                "the lunch for?"
                            )
                        )
                    ]
                ),
                final=True,
            )

            return

        # =================================================
        # CASE 2:
        # Number of people is available.
        # =================================================

        number_of_people = int(number_match.group(1))

        print(f"Number of people : {number_of_people}")
        print("Preparing catering plan...")
        print()

        # -------------------------------------------------
        # Create a simple catering plan
        # -------------------------------------------------

        sandwiches = number_of_people
        drinks = number_of_people
        fruit_cups = max(1, number_of_people // 2)

        catering_plan = (
            f"CATERING LUNCH PLAN\n"
            f"\n"
            f"People: {number_of_people}\n"
            f"Sandwiches: {sandwiches}\n"
            f"Drinks: {drinks}\n"
            f"Fruit cups: {fruit_cups}\n"
            f"\n"
            f"The lunch plan is ready."
        )

        # -------------------------------------------------
        # Add final result as an ARTIFACT
        # -------------------------------------------------

        await updater.add_artifact(
            parts=[
                Part(
                    text=catering_plan,
                )
            ],
            name="Catering Lunch Plan",
        )

        # -------------------------------------------------
        # Mark SAME task as completed
        # -------------------------------------------------

        await updater.complete()

        print("Artifact created : Catering Lunch Plan")
        print("Task status      : COMPLETED")
        print()


    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        if context.context_id is None:
            raise ValueError("A2A context ID is required.")

        if context.task_id is None:
            raise ValueError("A2A task ID is required.")

        updater = TaskUpdater(
            event_queue,
            context.task_id,
            context.context_id,
        )

        await updater.cancel()


# =========================================================
# STEP 3: DEFINE CATERING SKILL
# =========================================================

catering_skill = AgentSkill(
    id="catering-specialist",
    name="Catering Specialist",
    description=(
        "Prepares catering and group lunch plans. "
        "The specialist may request additional information "
        "such as the number of people before completing the plan."
    ),
    tags=[
        "catering",
        "group lunch",
        "team lunch",
        "food",
    ],
    examples=[
        "Prepare lunch for my team",
        "Arrange catering for 20 people",
        "I need lunch for a group",
    ],
)


# =========================================================
# STEP 4: CREATE AGENT CARD
# =========================================================

catering_agent_card = AgentCard(
    name="Catering Agent",
    description=(
        "A remote catering specialist that prepares "
        "group lunch plans."
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
        catering_skill,
    ],
)


# =========================================================
# STEP 5: CREATE REQUEST HANDLER
# =========================================================

catering_request_handler = DefaultRequestHandler(
    agent_executor=CateringAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=catering_agent_card,
)


# =========================================================
# STEP 6: CREATE A2A ROUTES
# =========================================================

routes = [
    *create_agent_card_routes(
        catering_agent_card,
    ),
    *create_jsonrpc_routes(
        catering_request_handler,
        "/",
    ),
]


# =========================================================
# STEP 7: CREATE STARLETTE SERVER
# =========================================================

app = Starlette(
    routes=routes,
)


# =========================================================
# STEP 8: START SERVER
# =========================================================

if __name__ == "__main__":

    print()
    print("==========================================")
    print("          CATERING AGENT SERVER")
    print("==========================================")
    print()
    print(f"Catering Agent : {AGENT_URL}")
    print()
    print("Waiting for A2A requests...")
    print()

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )