# LinkedIn Email Scraper + Gmail Sender

Scrape recent LinkedIn posts for emails by query/category and send personalized emails via Gmail API. Results are saved to a CSV with metadata and a date column so you can send only for a specific day.

Use this for personal/educational purposes only. Respect LinkedIn's Terms of Service and local laws.

## Repo structure

- `linkedin_email_scraper.py` — Selenium scraper (saves collected emails to CSV)
- `gmail_sender.py` — Gmail API sender with `--date` filter
- `search_queries.json` — Query categories and terms
- `requirements.txt` — Python dependencies
- `.gitignore` — Excludes secrets and generated files (CSV, tokens, venv, etc.)
- `README.md`

## Prerequisites

- macOS/Linux/Windows with Python 3.10+ (tested on 3.11)
- Google Chrome installed

## Setup

```bash
cd /Users/karangupta/Desktop/SRM/own/Projects/sathi.me

# 1) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2) Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## 1) Scrape emails from LinkedIn

Set your LinkedIn credentials via environment variables (or enter interactively when prompted):

```bash
export LINKEDIN_USERNAME="your.email@example.com"
export LINKEDIN_PASSWORD="your_password"

# Run with reliable defaults; results go to mail.csv
python linkedin_email_scraper.py \
  --max-scrolls 5 \
  --scroll-pause 3.0 \
  --tab-delay 4.0 \
  --category-delay 15.0 \
  --time-filter past-24h \
  --output mail.csv

# Run a specific category only (example: internships)
python linkedin_email_scraper.py --categories internship_searches --output mail.csv
```

The scraper will open Chrome, log in, search, expand "see more" sections, extract emails, and continuously append results to `mail.csv` after each query. It retries login and waits conservatively to avoid timeouts.

### CSV schema (mail.csv)

- `email` — extracted email address
- `category` — query category (e.g., internship_searches)
- `query` — the search query string
- `count` — number of occurrences for that (email, category, query)
- `date` — ISO date (YYYY-MM-DD) of the run when the row was saved

Tip: list which dates exist in your file

```bash
awk -F, 'NR>1 {print $5}' mail.csv | sort -u
```

## 2) Send emails via Gmail (by date)

First-time Gmail API setup (one-time):

1. Go to Google Cloud Console → create/select project
2. Enable the Gmail API
3. Create OAuth 2.0 Client ID (Desktop)
4. Download `credentials.json` into this folder (gitignored)
5. If your app is in testing mode, add your Gmail account under OAuth consent screen → Test users

Preview without sending (choose a date that exists in `mail.csv`):

```bash
python gmail_sender.py --csv mail.csv --date 2025-11-05 --dry-run --limit 5
```

Send a small batch (attaches `RESUME2.pdf`, adjust path/filename):

```bash
python gmail_sender.py \
  --csv mail.csv \
  --resume RESUME2.pdf \
  --date 2025-11-05 \
  --limit 10 \
  --delay 10
```

Notes:

- On first real send, a browser opens for Google login/consent. A `token.json` is saved (gitignored) for next runs.
- Use `--limit` to avoid blasting everyone at once; remove it only when you’re confident.
- If you see `Error 403: access_denied`, add your email under OAuth consent screen → Test users.

## Configuration: search queries

Edit `search_queries.json` to customize what you search for. Example categories:

- `internship_searches` — Software/Python/Backend intern roles
- `entry_level_searches` — Junior/Entry-level/Associate roles
- `Major` — Core roles (e.g., Software Engineer I, Full Stack Developer)
- `open_source_searches` — “good first issue”, “help wanted”, etc.

## Troubleshooting

- ChromeDriver: handled automatically via `webdriver-manager`.
- Login fails but browser shows you’re logged in: the script retries and uses multiple signals to detect login; watch for CAPTCHA and solve it manually.
- Empty send set: ensure `--date` matches a date present in `mail.csv` (see the awk command above).
- Gmail limits: normal Gmail sending limits apply.

## Ethics & legal

- Only use on accounts and data you’re authorized to access.
- Respect site terms, robots, and rate limits. This repo is for educational purposes only.

## License

MIT (or your preferred license)
