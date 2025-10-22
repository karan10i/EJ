# LinkedIn Email Scraper

This script logs in to LinkedIn using Selenium, scrolls through your feed or a specific post URL, extracts visible post text, finds email addresses using a regex, and writes unique emails to a CSV file.

Warning: Use this script only for personal/educational use and obey LinkedIn's terms of service.

Prerequisites
- Python 3.8+
- Chrome browser installed

Quick setup

```bash
# create virtualenv (macOS)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Usage

Set credentials via environment variables or enter them at prompt:

```bash
# export credentials (safer to use OS-level secret managers)
export LINKEDIN_USERNAME="your.email@example.com"
export LINKEDIN_PASSWORD="your_password"

# run against your feed
python linkedin_email_scraper.py --max-scrolls 20 --scroll-pause 2.5 --output emails.csv

# run against a particular post or profile/feed URL
python linkedin_email_scraper.py --url "https://www.linkedin.com/feed/update/urn:li:activity:..." --max-scrolls 5
```

Notes & Best practices
- Do not hardcode credentials in code. Use environment variables or interactive prompt.
- Be conservative with scrolls and pauses to avoid triggering anti-bot measures.
- Consider using a real browser (non-headless) to reduce detection likelihood.
- This script is a simple educational example. For production or heavy scraping, consider respectful rate-limiting and legal compliance.
