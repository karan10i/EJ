"""
Gmail API sender for scraped emails

This script reads emails from a CSV (from linkedin_email_scraper.py),
generates personalized content, and sends messages via the Gmail API using
OAuth2 (no app password required). On first run, it opens a browser window for
Google login and consent, then saves a token for subsequent runs.

Prerequisites
- Enable the Gmail API in your Google Cloud project
- Create OAuth Client ID (Desktop app)
- Download credentials.json into this folder
- pip install -r requirements.txt

Usage
    # First run will open browser for Google login/consent
    python gmail_sender.py --csv emails.csv --resume RESUME2.pdf --limit 3 --delay 10

    # Dry run to preview without sending
    python gmail_sender.py --csv emails.csv --resume RESUME2.pdf --dry-run

Notes
- OAuth token saved to token.json (gitignored)
- Daily limits apply (similar to Gmail sending limits)
"""

import os
import csv
import time
import base64
import argparse
from typing import Dict, List, Set
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import socket

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_template_for_job(job_title: str):
    subject = f"{job_title} Application - Karan Gupta"
    body = f"""Hi,

I am writing to express my strong interest in the \"{job_title}\" role as advertised on LinkedIn. With hands-on experience in Node.js and JavaScript development, including building robust and responsive web applications, scalable APIs, and optimizing backend systems for efficient performance, I am confident in my ability to contribute effectively to your engineering team.

My technical expertise encompasses Node.js, Express.js, MongoDB, Dyjango, Flask, Web Templates, React, microservices architecture, and CI/CD automation using tools like Jenkins and GitHub Actions. I have a proven track record of delivering scalable solutions—such as a real-time, browser-based SSH control plane and high-performance CI/CD-backed deployments—that streamline user experiences and ensure system reliability.

I am eager to apply my skills and learn in a dynamic environment, ideally starting with an open-source project to further sharpen my expertise and add value to your projects. My attached resume provides more details on my background and qualifications.

Thank you for your time and consideration.

Love,
Karan Gupta
"""
    return subject, body


def read_emails_from_csv(csv_path: str, filter_date: str = None) -> List[Dict[str, str]]:
    """Read rows from CSV, optionally filtering by exact date in 'date' column.

    Args:
        csv_path: Path to CSV (expects headers: email, category, query, [date])
        filter_date: YYYY-MM-DD string to include only rows with this date (optional)

    Returns: List of dicts with keys: email, category, query, date (if present)
    """
    emails: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = (row.get("email") or "").strip()
            category = (row.get("category") or "").strip()
            query = (row.get("query") or "").strip()
            date = (row.get("date") or "").strip()
            if not email:
                continue
            if filter_date is not None and date != filter_date:
                continue
            emails.append({
                "email": email,
                "category": category,
                "query": query,
                "date": date,
            })
    return emails


def unique_by_email(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    uniq = {}
    for r in rows:
        e = r["email"].lower()
        if e not in uniq:
            uniq[e] = r
    return uniq


def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise RuntimeError("Missing credentials.json. Follow README to create and download it.")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def build_message(sender: str, to: str, subject: str, body_text: str, attachment_path: str = None):
    message = MIMEMultipart()
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject

    message.attach(MIMEText(body_text, "plain"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment_path)}",
            )
            message.attach(part)
            print(f"    📎 Attached: {os.path.basename(attachment_path)} ({os.path.getsize(attachment_path)} bytes)")
    elif attachment_path:
        print(f"    ⚠️  Attachment not found: {attachment_path}")

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_message(service, user_id: str, message: Dict, max_retries: int = 3) -> bool:
    """Send message with retry logic for network errors."""
    for attempt in range(1, max_retries + 1):
        try:
            service.users().messages().send(userId=user_id, body=message).execute()
            return True
        except HttpError as e:
            print(f"    ✗ Gmail API error: {e}")
            return False
        except (socket.timeout, TimeoutError, ConnectionError, OSError) as e:
            if attempt < max_retries:
                wait = attempt * 5  # 5s, 10s, 15s
                print(f"    ⚠️  Network error (attempt {attempt}/{max_retries}): {type(e).__name__}")
                print(f"    ⏳ Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    ✗ Failed after {max_retries} retries: {type(e).__name__}")
                return False
        except Exception as e:
            print(f"    ✗ Unexpected error: {e}")
            return False
    return False


def load_sent_emails(log_file: str) -> Set[str]:
    """Load set of emails already sent from log file."""
    if not os.path.exists(log_file):
        return set()
    with open(log_file, "r", encoding="utf-8") as f:
        return set(line.strip().lower() for line in f if line.strip())


def mark_email_sent(log_file: str, email: str):
    """Append email to sent log file."""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{email.lower()}\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    parser = argparse.ArgumentParser(description="Send emails via Gmail API from CSV")
    parser.add_argument("--csv", default="mail.csv", help="Path to CSV with columns: email,category,query,date")
    parser.add_argument("--resume", default="RESUME2.pdf", help="Path to resume PDF")
    parser.add_argument("--sender", default=None, help="Optional explicit From email (defaults to your Gmail)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    parser.add_argument("--limit", type=int, help="Limit number of emails to send")
    parser.add_argument("--delay", type=float, default=5.0, help="Seconds to wait between sends")
    parser.add_argument("--date", type=str, default=None, help="Only send emails from this date (YYYY-MM-DD) in mail.csv")
    parser.add_argument("--sent-log", type=str, default="sent_emails.log", help="Log file to track sent emails (resume capability)")
    parser.add_argument("--reset-log", action="store_true", help="Clear sent log and start fresh")
    args = parser.parse_args()

    # Handle sent log reset
    if args.reset_log and os.path.exists(args.sent_log):
        os.remove(args.sent_log)
        print(f"🗑️  Cleared sent log: {args.sent_log}")

    rows = read_emails_from_csv(args.csv, filter_date=args.date)
    uniq = unique_by_email(rows)
    if not uniq:
        print("No emails found in CSV.")
        return

    # Load already-sent emails to avoid duplicates on resume
    sent_emails = load_sent_emails(args.sent_log) if not args.dry_run else set()
    remaining = {e: info for e, info in uniq.items() if e.lower() not in sent_emails}

    print(f"Loaded {len(uniq)} unique recipients from {args.csv}")
    if sent_emails:
        print(f"📋 Already sent to {len(sent_emails)} recipients (skipping them)")
        print(f"📬 Remaining to send: {len(remaining)}")
    
    if not remaining and not args.dry_run:
        print("✅ All recipients already contacted. Use --reset-log to start fresh.")
        return
    
    # Use remaining instead of uniq for actual sending
    uniq = remaining if not args.dry_run else uniq

    # Preview mode
    if args.dry_run:
        print("\n🔍 DRY RUN - No emails will be sent\n")
        for i, (email, info) in enumerate(uniq.items(), 1):
            subject, body = get_template_for_job(info["query"])
            print(f"[{i}] To: {email}")
            print(f"    Subject: {subject}")
            print(f"    Body: {body[:120]}...")
            if args.limit and i >= args.limit:
                break
        return

    service = get_gmail_service()

    sent = 0
    for i, (email, info) in enumerate(uniq.items(), 1):
        if args.limit and sent >= args.limit:
            break
        subject, body = get_template_for_job(info["query"])
        # Note: 'me' userId uses the authorized account from OAuth
        msg = build_message(args.sender or "me", email, subject, body, args.resume)
        print(f"[{i}] Sending to: {email}  |  Subject: {subject}")
        ok = send_message(service, user_id="me", message=msg, max_retries=3)
        if ok:
            print("    ✓ Sent")
            mark_email_sent(args.sent_log, email)
            sent += 1
        else:
            print("    ✗ Failed (will retry on next run)")
        if i < len(uniq):
            time.sleep(args.delay)

    print(f"\nCompleted. Sent {sent} messages.")


if __name__ == "__main__":
    main()
