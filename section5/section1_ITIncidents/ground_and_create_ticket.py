import json
import urllib.request

from ground_incident import retrieve_incidents, ground_incident


TICKET_API_URL = "http://127.0.0.1:8000/api/incidents"


def create_ticket(grounded_result: dict, description: str):
    payload = {
        "category": grounded_result["recommended_category"],
        "priority": grounded_result["recommended_priority"],
        "support_team": grounded_result["recommended_support_team"],
        "description": description,
        "similar_incidents": grounded_result.get("similar_incidents", []),
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        TICKET_API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main():

    new_incident = (
        "During a customer presentation, Microsoft Teams keeps "
        "disconnecting and reconnecting. Other internet applications "
        "are working normally."
    )

    print("\n=== Retrieving Similar Incidents ===")

    retrieved_incidents = retrieve_incidents(new_incident)

    print("\nRetrieved incidents:")
    print(json.dumps(retrieved_incidents, indent=2))

    print("\n=== Grounding Incident ===")

    grounded_result = ground_incident(
        new_incident,
        retrieved_incidents,
    )

    print("\nGrounded decision:")
    print(json.dumps(grounded_result, indent=2))

    print("\n=== Creating IT Ticket ===")

    ticket_result = create_ticket(
        grounded_result,
        new_incident,
    )

    print("\nTicket created:")
    print(json.dumps(ticket_result, indent=2))


if __name__ == "__main__":
    main()