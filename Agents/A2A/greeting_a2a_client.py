import asyncio

import httpx

from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent


# ---------------------------------------------------------
# Greeting Agent is mounted at /greeting
# ---------------------------------------------------------
SERVER_URL = "http://127.0.0.1:8000/greeting"


async def main():

    print()
    print("==========================================")
    print("          A2A GREETING CLIENT")
    print("==========================================")
    print()

    # ---------------------------------------------------------
    # STEP 1: Create HTTP client
    # ---------------------------------------------------------
    async with httpx.AsyncClient(timeout=60.0) as http_client:

        # -----------------------------------------------------
        # STEP 2: Discover Greeting Agent
        # -----------------------------------------------------
        print("1. Discovering Greeting Agent...")

        resolver = A2ACardResolver(
            httpx_client=http_client,
            base_url=SERVER_URL,
        )

        agent_card = await resolver.get_agent_card()

        # -----------------------------------------------------
        # STEP 3: Display discovered Agent Card
        # -----------------------------------------------------
        print()
        print("Agent Card discovered successfully!")
        print()
        print(f"Name        : {agent_card.name}")
        print(f"Description : {agent_card.description}")
        print(f"Version     : {agent_card.version}")

        print()
        print("Skills:")

        for skill in agent_card.skills:
            print(f"  - {skill.name}: {skill.description}")

        # -----------------------------------------------------
        # STEP 4: Create remote A2A Agent
        # -----------------------------------------------------
        async with A2AAgent(
            agent_card=agent_card,
        ) as remote_agent:

            # -------------------------------------------------
            # STEP 5: Send message to remote Greeting Agent
            # -------------------------------------------------
            message = "Good morning"

            print()
            print(f'Sending message: "{message}"')
            print()

            response = await remote_agent.run(message)

            # -------------------------------------------------
            # STEP 6: Display response
            # -------------------------------------------------
            print("Greeting Agent response:")
            print()

            for response_message in response.messages:
                if response_message.text:
                    print(response_message.text)


if __name__ == "__main__":
    asyncio.run(main())