import asyncio
import os

from dotenv import load_dotenv
from azure.identity import AzureCliCredential

from agent_framework.a2a import A2AAgent
from agent_framework.foundry import FoundryChatClient


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")

COFFEE_AGENT_URL = "http://127.0.0.1:8001/"
SANDWICH_AGENT_URL = "http://127.0.0.1:8002/"


if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT is missing from .env")

if not MODEL_DEPLOYMENT_NAME:
    raise ValueError("MODEL_DEPLOYMENT_NAME is missing from .env")


async def main():

    # =====================================================
    # STEP 1: CREATE FOUNDRY CHAT CLIENT
    # =====================================================

    credential = AzureCliCredential()

    foundry_client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL_DEPLOYMENT_NAME,
        credential=credential,
    )


    # =====================================================
    # STEP 2: CREATE LOCAL A2A CLIENT FOR COFFEE AGENT
    # =====================================================

    coffee_agent = A2AAgent(
        name="CoffeeSpecialist",
        description=(
            "Coffee specialist. Use this agent for coffee-related "
            "requests such as espresso, latte, cappuccino, americano, "
            "mocha, or coffee recommendations."
        ),
        url=COFFEE_AGENT_URL,
    )


    # =====================================================
    # STEP 3: CREATE LOCAL A2A CLIENT FOR SANDWICH AGENT
    # =====================================================

    sandwich_agent = A2AAgent(
        name="SandwichSpecialist",
        description=(
            "Sandwich and lunch specialist. Use this agent for "
            "sandwich requests, lunch requests, or requests asking "
            "for something to eat."
        ),
        url=SANDWICH_AGENT_URL,
    )


    # =====================================================
    # STEP 4: CONVERT REMOTE A2A AGENTS INTO TOOLS
    # =====================================================

    coffee_tool = coffee_agent.as_tool(
        name="coffee_specialist",
        description=(
            "Ask the remote Coffee Specialist for help with coffee, "
            "espresso, latte, cappuccino, americano, mocha, "
            "or other coffee-related requests."
        ),
    )

    sandwich_tool = sandwich_agent.as_tool(
        name="sandwich_specialist",
        description=(
            "Ask the remote Sandwich Specialist for help with "
            "sandwiches, lunch, or other cafe food requests."
        ),
    )


    # =====================================================
    # STEP 5: CREATE CAFE COORDINATOR
    # =====================================================

    cafe_agent = foundry_client.as_agent(
        name="CafeAgent",
        instructions=(
            "You are the main Cafe Coordinator. "

            "When a customer asks about coffee or a coffee drink, "
            "use the coffee_specialist tool. "

            "When a customer asks about a sandwich, lunch, or something "
            "to eat, use the sandwich_specialist tool. "

            "For other general cafe questions, answer the customer "
            "yourself without calling either specialist. "

            "Choose the appropriate specialist based on the meaning "
            "of the customer's request."
        ),
        tools=[
            coffee_tool,
            sandwich_tool,
        ],
    )


    # =====================================================
    # STEP 6: INTERACTIVE CAFE
    # =====================================================

    print()
    print("==========================================")
    print("              CAFE AGENT")
    print("==========================================")
    print()
    print("Coffee Specialist   : http://127.0.0.1:8001/")
    print("Sandwich Specialist : http://127.0.0.1:8002/")
    print()
    print("Type 'exit' to stop.")
    print()


    try:

        while True:

            user_message = input("You: ").strip()

            if user_message.lower() == "exit":
                print()
                print("Cafe Agent stopped.")
                break

            if not user_message:
                continue

            try:

                response = await cafe_agent.run(user_message)

                print()
                print("Cafe Agent:")
                print(response.text)
                print()

            except Exception as error:

                print()
                print("ERROR:")
                print(error)
                print()

    finally:

        await coffee_agent.close()
        await sandwich_agent.close()


if __name__ == "__main__":
    asyncio.run(main())