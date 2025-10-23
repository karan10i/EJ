"""
Email sender for scraped LinkedIn emails

This script reads emails from a CSV file (output of linkedin_email_scraper.py),
generates personalized email templates based on the query category, and sends
emails using Gmail SMTP.

Usage:
    python send_emails.py --csv emails.csv --resume RESUME2.pdf

Configuration:
    Set environment variables:
    - SENDER_EMAIL: Your Gmail address (e.g., karan.gup10@gmail.com)
    - SENDER_PASSWORD: Your Gmail app password (not regular password!)
    
    To create Gmail app password:
    1. Go to Google Account > Security > 2-Step Verification
    2. Scroll to "App passwords"
    3. Generate password for "Mail" app
"""

import csv
import smtplib
import argparse
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import getpass
from datetime import datetime


# Email templates by category
TEMPLATES = {
    "internship_searches": {
        "subject": "Software Engineering Intern Application - Karan Gupta",
        "body": """Hi,

I am writing to express my strong interest in the {query} role. As a passionate software engineer with five years of hands-on experience in full-stack development, I am eager to contribute to your team through an internship opportunity.

My technical expertise includes:
• Node.js, Express.js, and JavaScript development
• React and modern frontend frameworks
• MongoDB and database design
• Building scalable APIs and microservices architecture
• CI/CD automation with Jenkins and GitHub Actions

I have successfully delivered projects such as a real-time browser-based SSH control plane and high-performance CI/CD-backed deployments that streamline user experiences and ensure system reliability.

I am excited about the opportunity to learn, grow, and contribute to your engineering team. My attached resume provides comprehensive details about my background and qualifications.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team.

Best regards,
Karan Gupta
karan.gup10@gmail.com"""
    },
    
    "entry_level_searches": {
        "subject": "Entry-Level Software Engineer Application - Karan Gupta",
        "body": """Hi,

I am writing to express my strong interest in the {query} position as advertised on LinkedIn. With five years of hands-on experience in Node.js and JavaScript development, including building robust and responsive web applications, scalable APIs, and optimizing backend systems for efficient performance, I am confident in my ability to contribute effectively to your engineering team.

My technical expertise encompasses:
• Node.js, Express.js, and MongoDB
• React and modern web application development
• Microservices architecture and RESTful API design
• CI/CD automation using Jenkins and GitHub Actions
• Database optimization and performance tuning

I have a proven track record of delivering scalable solutions—such as a real-time, browser-based SSH control plane and high-performance CI/CD-backed deployments—that streamline user experiences and ensure system reliability.

I am eager to apply my skills in a dynamic environment and contribute to impactful projects. My attached resume provides more details on my background and qualifications.

Thank you for your time and consideration.

Best regards,
Karan Gupta
karan.gup10@gmail.com"""
    },
    
    "open_source_searches": {
        "subject": "Interested in Contributing to Your Open Source Project",
        "body": """Hi,

I came across your post regarding "{query}" and I'm very interested in contributing to your open source project.

I'm a software engineer with five years of experience in full-stack development, specializing in:
• Node.js and JavaScript ecosystems
• React and frontend development
• API development and microservices
• DevOps and CI/CD automation

I'm particularly drawn to open source contributions as they allow me to collaborate with talented developers, improve my skills, and give back to the community. I've worked on scalable web applications and have experience with modern development workflows.

I'd love to learn more about how I can contribute to your project. Please let me know if there are any tasks or issues that would be a good fit for my skillset.

Looking forward to collaborating with you!

Best regards,
Karan Gupta
karan.gup10@gmail.com"""
    }
}


def get_email_credentials():
    """Get email credentials from environment or prompt."""
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    
    if sender_email and sender_password:
        print(f"Using credentials from environment for: {sender_email}")
        return sender_email, sender_password
    
    print("\n⚠️  Email credentials not found in environment variables")
    print("Please provide your Gmail credentials:")
    sender_email = input("Gmail address: ").strip()
    sender_password = getpass.getpass("Gmail app password: ")
    
    return sender_email, sender_password


def read_emails_from_csv(csv_path):
    """Read emails from CSV file.
    
    Returns list of dicts with 'email', 'category', 'query' keys.
    """
    emails = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                emails.append({
                    'email': row['email'],
                    'category': row['category'],
                    'query': row['query']
                })
        print(f"✓ Loaded {len(emails)} email entries from {csv_path}")
        return emails
    except FileNotFoundError:
        print(f"✗ Error: CSV file not found: {csv_path}")
        return []
    except Exception as e:
        print(f"✗ Error reading CSV: {e}")
        return []


def generate_email_content(recipient, category, query):
    """Generate personalized email subject and body.
    
    Args:
        recipient: Email address
        category: Query category (e.g., 'internship_searches')
        query: Specific search query
    
    Returns:
        Tuple of (subject, body)
    """
    template = TEMPLATES.get(category, TEMPLATES["entry_level_searches"])
    
    subject = template["subject"]
    body = template["body"].format(query=query)
    
    return subject, body


def send_email(sender_email, sender_password, recipient, subject, body, resume_path=None):
    """Send an email with optional resume attachment.
    
    Args:
        sender_email: Sender's Gmail address
        sender_password: Sender's Gmail app password
        recipient: Recipient email address
        subject: Email subject
        body: Email body text
        resume_path: Optional path to resume PDF
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach resume if provided
        if resume_path and os.path.exists(resume_path):
            with open(resume_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(resume_path)}'
                )
                msg.attach(part)
        
        # Connect to Gmail SMTP server and send
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"    ✗ Error sending to {recipient}: {e}")
        return False


def load_sent_log(log_path='sent_emails.log'):
    """Load list of already-sent email addresses."""
    if not os.path.exists(log_path):
        return set()
    
    with open(log_path, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())


def save_to_sent_log(email, log_path='sent_emails.log'):
    """Append email address to sent log."""
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{email}\n")


def main():
    parser = argparse.ArgumentParser(description='Send emails to scraped LinkedIn contacts')
    parser.add_argument('--csv', type=str, default='emails.csv',
                        help='Path to CSV file with emails (from linkedin_email_scraper.py)')
    parser.add_argument('--resume', type=str, default='RESUME2.pdf',
                        help='Path to resume PDF to attach')
    parser.add_argument('--delay', type=float, default=5.0,
                        help='Seconds to wait between emails (avoid rate limiting)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview emails without actually sending them')
    parser.add_argument('--limit', type=int,
                        help='Maximum number of emails to send (for testing)')
    args = parser.parse_args()
    
    # Load emails from CSV
    email_list = read_emails_from_csv(args.csv)
    if not email_list:
        print("No emails to send. Exiting.")
        return
    
    # Deduplicate emails (same email may appear multiple times)
    unique_emails = {}
    for entry in email_list:
        email = entry['email']
        if email not in unique_emails:
            unique_emails[email] = entry
    
    print(f"✓ Found {len(unique_emails)} unique email addresses")
    
    # Load sent log to avoid duplicates
    sent_log = load_sent_log()
    emails_to_send = {k: v for k, v in unique_emails.items() if k not in sent_log}
    
    if len(sent_log) > 0:
        print(f"⚠️  Skipping {len(unique_emails) - len(emails_to_send)} already-sent emails")
    
    if not emails_to_send:
        print("✓ All emails have already been sent!")
        return
    
    # Apply limit if specified
    if args.limit:
        emails_to_send = dict(list(emails_to_send.items())[:args.limit])
        print(f"⚠️  Limited to {args.limit} emails for this run")
    
    print(f"\n📧 Will send {len(emails_to_send)} emails")
    
    # Check resume exists
    if args.resume and not os.path.exists(args.resume):
        print(f"⚠️  Warning: Resume file not found: {args.resume}")
        proceed = input("Continue without resume attachment? (y/n): ").strip().lower()
        if proceed != 'y':
            return
        args.resume = None
    
    # Dry run mode
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No emails will be sent\n")
        for idx, (recipient, info) in enumerate(emails_to_send.items(), 1):
            subject, body = generate_email_content(recipient, info['category'], info['query'])
            print(f"[{idx}/{len(emails_to_send)}] To: {recipient}")
            print(f"  Category: {info['category']}")
            print(f"  Query: {info['query']}")
            print(f"  Subject: {subject}")
            print(f"  Body preview: {body[:100]}...")
            print()
        return
    
    # Get credentials
    sender_email, sender_password = get_email_credentials()
    
    # Send emails
    print(f"\n{'='*60}")
    print("Starting email campaign")
    print(f"{'='*60}\n")
    
    sent_count = 0
    failed_count = 0
    
    for idx, (recipient, info) in enumerate(emails_to_send.items(), 1):
        print(f"[{idx}/{len(emails_to_send)}] Sending to: {recipient}")
        print(f"  Category: {info['category']}")
        print(f"  Query: {info['query']}")
        
        subject, body = generate_email_content(recipient, info['category'], info['query'])
        
        success = send_email(sender_email, sender_password, recipient, 
                           subject, body, args.resume)
        
        if success:
            print(f"  ✓ Sent successfully")
            save_to_sent_log(recipient)
            sent_count += 1
        else:
            failed_count += 1
        
        # Rate limiting delay
        if idx < len(emails_to_send):
            print(f"  ⏸  Waiting {args.delay}s before next email...\n")
            time.sleep(args.delay)
    
    print(f"\n{'='*60}")
    print(f"✓ Campaign complete!")
    print(f"  Sent: {sent_count}")
    print(f"  Failed: {failed_count}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
