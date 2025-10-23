# Email Sender for LinkedIn Scraper

This script reads the CSV output from `linkedin_email_scraper.py` and sends personalized emails based on the query category (internships, entry-level, open-source).

## Setup

### 1. Create Gmail App Password

**IMPORTANT:** Don't use your regular Gmail password. Create an app password:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification if not already enabled
3. Go to "App passwords" (search for it in settings)
4. Select "Mail" and your device
5. Copy the 16-character password

### 2. Set Environment Variables

```bash
export SENDER_EMAIL="karan.gup10@gmail.com"
export SENDER_PASSWORD="your-16-char-app-password"
```

Or add to your `~/.zshrc`:
```bash
echo 'export SENDER_EMAIL="karan.gup10@gmail.com"' >> ~/.zshrc
echo 'export SENDER_PASSWORD="xxxx xxxx xxxx xxxx"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

### Dry run (preview without sending)
```bash
python send_emails.py --csv emails.csv --resume RESUME2.pdf --dry-run
```

### Send to first 3 emails (testing)
```bash
python send_emails.py --csv emails.csv --resume RESUME2.pdf --limit 3
```

### Send to all emails
```bash
python send_emails.py --csv emails.csv --resume RESUME2.pdf --delay 10
```

### Custom options
```bash
python send_emails.py \
  --csv emails.csv \
  --resume RESUME2.pdf \
  --delay 15 \
  --limit 50
```

## Features

### Personalized Templates
- **Internship emails**: Emphasizes learning, growth, internship interest
- **Entry-level emails**: Professional tone, highlights experience
- **Open-source emails**: Collaborative, contribution-focused

### Duplicate Prevention
- Tracks sent emails in `sent_emails.log`
- Automatically skips already-sent addresses
- Safe to re-run without spamming

### Rate Limiting
- Default 5s delay between emails
- Prevents Gmail rate limiting
- Adjustable with `--delay` flag

### Resume Attachment
- Automatically attaches RESUME2.pdf (or custom path)
- Validates file exists before sending

## Email Templates

Templates are in `send_emails.py` under the `TEMPLATES` dict. Customize them based on your resume:

```python
TEMPLATES = {
    "internship_searches": {
        "subject": "...",
        "body": "..."
    },
    ...
}
```

## Output

```
✓ Loaded 45 email entries from emails.csv
✓ Found 23 unique email addresses
⚠️  Skipping 5 already-sent emails

📧 Will send 18 emails

============================================================
Starting email campaign
============================================================

[1/18] Sending to: recruiter@company.com
  Category: internship_searches
  Query: Software Engineering Intern
  ✓ Sent successfully
  ⏸  Waiting 5s before next email...

[2/18] Sending to: hr@startup.io
  ...
```

## Troubleshooting

### "Username and Password not accepted"
- Make sure you're using an **app password**, not your regular Gmail password
- Verify 2-Step Verification is enabled

### "Daily sending limit exceeded"
- Gmail limits: 500 emails/day for regular accounts
- Wait 24 hours or use `--limit` to send in batches

### "Resume not found"
- Check the file path: `--resume RESUME2.pdf`
- Use absolute path if needed: `--resume /full/path/to/RESUME2.pdf`
