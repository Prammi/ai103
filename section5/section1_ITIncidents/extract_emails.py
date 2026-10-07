from email import policy
from email.parser import BytesParser
from pathlib import Path


EMAILS_FOLDER = Path("emails")
ATTACHMENTS_FOLDER = Path("attachments")


def extract_email(email_path: Path) -> dict:
    """Read one .eml file and extract its content and attachments."""

    with email_path.open("rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    body = ""
    attachments = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()

            # Extract email body
            if content_type == "text/plain" and disposition != "attachment":
                body = part.get_content()

            # Extract actual attachment
            elif disposition == "attachment":
                filename = part.get_filename()

                if not filename:
                    continue

                attachment_data = part.get_payload(decode=True)

                if not attachment_data:
                    continue

                output_path = ATTACHMENTS_FOLDER / filename

                output_path.write_bytes(attachment_data)

                attachments.append(
                    {
                        "filename": filename,
                        "content_type": content_type,
                        "path": str(output_path),
                        "size": len(attachment_data),
                    }
                )

    else:
        body = message.get_content()

    return {
        "from": message.get("From"),
        "to": message.get("To"),
        "subject": message.get("Subject"),
        "date": message.get("Date"),
        "body": body.strip(),
        "attachments": attachments,
    }


def main():
    # Make sure the attachments directory exists.
    ATTACHMENTS_FOLDER.mkdir(parents=True, exist_ok=True)

    email_files = sorted(EMAILS_FOLDER.glob("*.eml"))

    if not email_files:
        print("No .eml files found in the emails folder.")
        return

    for email_path in email_files:

        print("=" * 70)
        print(f"FILE: {email_path.name}")
        print("=" * 70)

        incident = extract_email(email_path)

        print(f"From       : {incident['from']}")
        print(f"To         : {incident['to']}")
        print(f"Subject    : {incident['subject']}")
        print(f"Date       : {incident['date']}")

        print("\nBODY:")
        print(incident["body"])

        print("\nATTACHMENTS:")

        if incident["attachments"]:
            for attachment in incident["attachments"]:
                print(f"  Filename     : {attachment['filename']}")
                print(f"  Content Type : {attachment['content_type']}")
                print(f"  Path         : {attachment['path']}")
                print(f"  Size         : {attachment['size']} bytes")
        else:
            print("  No attachments found.")

        print()


if __name__ == "__main__":
    main()