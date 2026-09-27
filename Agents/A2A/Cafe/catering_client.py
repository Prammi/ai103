import asyncio

from agent_framework import AgentSession
from agent_framework.a2a import A2AAgent


# =========================================================
# CONFIGURATION
# =========================================================

CATERING_AGENT_URL = "http://127.0.0.1:8003/"


async def main():

    print()
    print("==========================================")
    print("          CATERING A2A CLIENT")
    print("==========================================")
    print()

    # =====================================================
    # STEP 1: CREATE A2A CLIENT
    # =====================================================

    async with A2AAgent(
        name="CateringSpecialist",
        description="Remote catering specialist",
        url=CATERING_AGENT_URL,
    ) as catering_agent:

        # =================================================
        # STEP 2: CREATE SESSION
        #
        # This is IMPORTANT.
        #
        # The session remembers:
        # - context_id
        # - task_id
        # - task_state
        #
        # This allows the second message to continue
        # the SAME A2A task.
        # =================================================

        session = AgentSession()

        # =================================================
        # STEP 3: SEND FIRST MESSAGE
        # =================================================

        first_message = "Prepare lunch for my team"

        print(f"CLIENT -> CATERING AGENT:")
        print(first_message)
        print()

        first_response = await catering_agent.run(
            first_message,
            session=session,
        )

        print("------------------------------------------")
        print("CATERING AGENT RESPONSE")
        print("------------------------------------------")
        print()

        print(first_response.text)
        print()

        # =================================================
        # STEP 4: INSPECT SESSION
        #
        # After INPUT_REQUIRED, the session should now
        # contain the remote task information.
        # =================================================

        print("------------------------------------------")
        print("A2A SESSION AFTER FIRST MESSAGE")
        print("------------------------------------------")
        print()

        print(f"Service Session ID:")
        print(session.service_session_id)
        print()

        # =================================================
        # STEP 5: USER PROVIDES MISSING INFORMATION
        # =================================================

        user_answer = input("Your answer: ").strip()

        if not user_answer:
            print("No answer provided.")
            return

        print()
        print(f"CLIENT -> CATERING AGENT:")
        print(user_answer)
        print()

        # =================================================
        # STEP 6: SEND SECOND MESSAGE
        #
        # VERY IMPORTANT:
        #
        # We pass the SAME session.
        #
        # Because the previous task was INPUT_REQUIRED,
        # A2AAgent knows that this message belongs to
        # that existing task.
        # =================================================

        second_response = await catering_agent.run(
            user_answer,
            session=session,
        )

        print("------------------------------------------")
        print("CATERING AGENT FINAL RESPONSE")
        print("------------------------------------------")
        print()

        print(second_response.text)
        print()

        # =================================================
        # STEP 7: INSPECT SESSION AGAIN
        # =================================================

        print("------------------------------------------")
        print("A2A SESSION AFTER SECOND MESSAGE")
        print("------------------------------------------")
        print()

        print(f"Service Session ID:")
        print(session.service_session_id)
        print()


if __name__ == "__main__":
    asyncio.run(main())