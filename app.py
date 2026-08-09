import csv
import re
import base64
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# ============================================================
# CONFIGURATION
# ============================================================

CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")

RECIPIENTS_FILE = Path("recipients.csv")
RESUME_FILE = Path("resume.pdf")

LOG_DIR = Path("logs")
STATUS_FILE = LOG_DIR / "sending_status.csv"

# ------------------------------------------------------------
# SAFETY SETTINGS
# ------------------------------------------------------------

# Keep this TRUE while testing.
# When you are completely satisfied with the test,
# change it to False.
TEST_MODE = False

# In TEST_MODE, only this many emails can be sent.
MAX_EMAILS_PER_RUN = 200

# Gmail permission: send email only.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


# ============================================================
# EMAIL SUBJECT
# ============================================================

EMAIL_SUBJECT = (
    "Application for Software Engineer Role | "
    "~3 YOE | Immediate Joiner | Mahesh S R"
)


# ============================================================
# EMAIL BODY
# ============================================================

EMAIL_BODY = """Hello Hiring Team,

I hope you’re doing well.

I came across a job opportunity posted that aligns closely with my experience. I’m a Java-focused Fullstack Developer with ~3 years of experience building scalable, high-performance systems at Razorpay and Zoop.one.

At Razorpay, I developed backend services for high-scale financial systems, working on REST APIs, database optimization, and system reliability. At Zoop.one, I built microservices using Java and Spring Boot, handling 10K+ daily transactions and improving API latency by 20%.

My experience includes backend development, API design, and solving performance-critical problems in production systems. I’m confident I can contribute effectively to your team.

I have attached my resume and would value the opportunity to interview and showcase how I can add value to your team.

Best regards,
Mahesh S R
+91 9620540346
linkedin.com/in/maheshraokashyap/
"""


# ============================================================
# GMAIL AUTHENTICATION
# ============================================================

def authenticate_gmail():

    credentials = None

    # --------------------------------------------------------
    # Load existing OAuth token
    # --------------------------------------------------------

    if TOKEN_FILE.exists():

        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # --------------------------------------------------------
    # Refresh expired token
    # --------------------------------------------------------

    if (
        credentials
        and credentials.expired
        and credentials.refresh_token
    ):

        credentials.refresh(Request())

    # --------------------------------------------------------
    # Start OAuth flow if necessary
    # --------------------------------------------------------

    if not credentials or not credentials.valid:

        if not CREDENTIALS_FILE.exists():

            raise FileNotFoundError(
                "credentials.json was not found."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
        )

        credentials = flow.run_local_server(
            port=0
        )

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8"
        )

    return build(
        "gmail",
        "v1",
        credentials=credentials
    )


# ============================================================
# EMAIL VALIDATION
# ============================================================

def is_valid_email(email):

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return bool(
        re.match(pattern, email)
    )


# ============================================================
# LOAD RECIPIENTS
# ============================================================

def load_recipients():

    if not RECIPIENTS_FILE.exists():

        raise FileNotFoundError(
            f"{RECIPIENTS_FILE} was not found."
        )

    recipients = []
    seen = set()

    with RECIPIENTS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:

            raise ValueError(
                "recipients.csv is empty."
            )

        # ----------------------------------------------------
        # CSV must contain an "email" column
        # ----------------------------------------------------

        if "email" not in reader.fieldnames:

            raise ValueError(
                "recipients.csv must contain "
                "an 'email' column."
            )

        for row_number, row in enumerate(
            reader,
            start=2
        ):

            email = row.get(
                "email",
                ""
            ).strip()

            # ------------------------------------------------
            # Skip empty rows
            # ------------------------------------------------

            if not email:
                continue

            # ------------------------------------------------
            # Remove accidental whitespace
            # ------------------------------------------------

            email = email.strip()

            # ------------------------------------------------
            # Validate email
            # ------------------------------------------------

            if not is_valid_email(email):

                print(
                    f"WARNING: Invalid email on row "
                    f"{row_number}: {email}"
                )

                continue

            # ------------------------------------------------
            # Duplicate detection
            # ------------------------------------------------

            email_key = email.lower()

            if email_key in seen:

                print(
                    f"WARNING: Duplicate skipped: "
                    f"{email}"
                )

                continue

            seen.add(email_key)

            recipients.append(email)

    return recipients


# ============================================================
# LOAD PREVIOUSLY SENT EMAILS
# ============================================================

def load_sent_emails():

    sent_emails = set()

    if not STATUS_FILE.exists():

        return sent_emails

    with STATUS_FILE.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            email = row.get(
                "email",
                ""
            ).strip().lower()

            status = row.get(
                "status",
                ""
            ).strip().upper()

            if email and status == "SENT":

                sent_emails.add(email)

    return sent_emails


# ============================================================
# CREATE EMAIL
# ============================================================

def create_email(recipient):

    message = EmailMessage()

    # --------------------------------------------------------
    # Recipient
    # --------------------------------------------------------

    message["To"] = recipient

    # --------------------------------------------------------
    # Subject
    # --------------------------------------------------------

    message["Subject"] = EMAIL_SUBJECT

    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

    message.set_content(
        EMAIL_BODY
    )

    # --------------------------------------------------------
    # Attach ONLY resume.pdf
    # --------------------------------------------------------

    with RESUME_FILE.open("rb") as file:

        message.add_attachment(
            file.read(),
            maintype="application",
            subtype="pdf",
            filename="Mahesh S R - Java DEV - 3 YRS Experience.pdf"
        )

    return message


# ============================================================
# SEND EMAIL THROUGH GMAIL
# ============================================================

def send_email(gmail, message):

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    body = {
        "raw": encoded_message
    }

    return gmail.users().messages().send(
        userId="me",
        body=body
    ).execute()


# ============================================================
# SAVE STATUS
# ============================================================

def save_status(
    email,
    status,
    reason=""
):

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    file_exists = STATUS_FILE.exists()

    with STATUS_FILE.open(
        "a",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.writer(file)

        # ----------------------------------------------------
        # Create header on first write
        # ----------------------------------------------------

        if not file_exists:

            writer.writerow([
                "timestamp",
                "email",
                "status",
                "reason"
            ])

        writer.writerow([
            datetime.now().isoformat(
                timespec="seconds"
            ),
            email,
            status,
            reason
        ])


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print()
    print("=" * 70)
    print("JOB APPLICATION EMAIL SYSTEM")
    print("=" * 70)
    print()

    # ========================================================
    # CHECK REQUIRED FILES
    # ========================================================

    required_files = [
        RECIPIENTS_FILE,
        RESUME_FILE
    ]

    for required_file in required_files:

        if not required_file.exists():

            raise FileNotFoundError(
                f"Required file not found: "
                f"{required_file}"
            )

    # ========================================================
    # LOAD RECIPIENTS
    # ========================================================

    print("Loading recipients...")

    recipients = load_recipients()

    if not recipients:

        print(
            "No valid recipients found."
        )

        return

    print(
        f"Valid recipients: "
        f"{len(recipients)}"
    )

    # ========================================================
    # LOAD PREVIOUSLY SENT EMAILS
    # ========================================================

    sent_emails = load_sent_emails()

    print(
        f"Already sent: "
        f"{len(sent_emails)}"
    )

    # ========================================================
    # REMOVE ALREADY SENT RECIPIENTS
    # ========================================================

    pending = [
        email
        for email in recipients
        if email.lower() not in sent_emails
    ]

    print(
        f"Pending: "
        f"{len(pending)}"
    )

    if not pending:

        print()
        print(
            "No pending recipients."
        )

        return

    # ========================================================
    # SAFETY LIMIT
    # ========================================================

    if TEST_MODE:

        pending = pending[
            :MAX_EMAILS_PER_RUN
        ]

        print()
        print(
            "TEST MODE ENABLED"
        )

        print(
            f"Maximum emails this run: "
            f"{MAX_EMAILS_PER_RUN}"
        )

    else:

        print()
        print(
            "PRODUCTION MODE ENABLED"
        )

        print(
            "The program is allowed to send "
            "to all pending recipients."
        )

    # ========================================================
    # DISPLAY RECIPIENTS
    # ========================================================

    print()
    print(
        "The following emails are ready to send:"
    )

    print()

    for index, email in enumerate(
        pending,
        start=1
    ):

        print(
            f"{index}. {email}"
        )

    # ========================================================
    # DISPLAY EMAIL INFORMATION
    # ========================================================

    print()
    print("-" * 70)
    print("EMAIL PREVIEW")
    print("-" * 70)

    print()
    print(
        f"Subject:\n{EMAIL_SUBJECT}"
    )

    print()
    print(
        "Attachment:"
    )

    print(
        "  - resume.pdf"
    )

    print()
    print(
        "Cover letter attachment:"
    )

    print(
        "  - NONE"
    )

    print()
    print(
        "Body:"
    )

    print(
        EMAIL_BODY
    )

    print("-" * 70)

    # ========================================================
    # CONFIRMATION
    # ========================================================

    print()

    confirmation = input(
        "Type SEND to continue: "
    ).strip()

    if confirmation != "SEND":

        print()
        print(
            "Sending cancelled."
        )

        return

    # ========================================================
    # CONNECT TO GMAIL
    # ========================================================

    print()
    print(
        "Connecting to Gmail..."
    )

    gmail = authenticate_gmail()

    print(
        "Connected successfully."
    )

    print()

    # ========================================================
    # SEND
    # ========================================================

    successful = 0
    failed = 0

    for index, email in enumerate(
        pending,
        start=1
    ):

        print(
            f"[{index}/{len(pending)}] "
            f"Sending to {email}..."
        )

        try:

            message = create_email(
                email
            )

            result = send_email(
                gmail,
                message
            )

            message_id = result.get(
                "id",
                ""
            )

            save_status(
                email=email,
                status="SENT",
                reason=(
                    f"Message ID: "
                    f"{message_id}"
                )
            )

            print(
                "    SUCCESS"
            )

            successful += 1

        except Exception as error:

            error_message = str(
                error
            )

            save_status(
                email=email,
                status="FAILED",
                reason=error_message
            )

            print(
                f"    FAILED: "
                f"{error_message}"
            )

            failed += 1

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("SENDING COMPLETE")
    print("=" * 70)

    print(
        f"Successful: "
        f"{successful}"
    )

    print(
        f"Failed: "
        f"{failed}"
    )

    print(
        f"Status file: "
        f"{STATUS_FILE}"
    )

    print()


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()