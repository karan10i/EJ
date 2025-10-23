# LinkedIn Email Scraper

This script logs in to LinkedIn using Selenium, runs multiple search queries across different hiring categories (internships, entry-level, open-source), opens each search in a separate tab within one browser window, extracts visible post text, finds email addresses using regex, and writes unique emails to a CSV file with query/category metadata.

Warning: Use this script only for personal/educational use and obey LinkedIn's terms of service.

## Prerequisites
- Python 3.8+
- Chrome browser installed

## Quick setup

```bash
# create virtualenv (macOS)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Edit `search_queries.json` to customize your search queries. The default configuration includes:
- **internship_searches**: Software engineering intern roles, tech-specific intern positions
- **entry_level_searches**: Junior/entry-level developer roles, new grad positions
- **open_source_searches**: GitHub contribution labels (good first issue, help wanted, etc.)

## Usage

Set credentials via environment variables or enter them at prompt:

```bash
# export credentials (safer to use OS-level secret managers)
export LINKEDIN_USERNAME="your.email@example.com"
export LINKEDIN_PASSWORD="your_password"

# NEW: Process categories one at a time (RECOMMENDED for reliability)
# This processes one category completely before moving to the next
python linkedin_email_scraper.py

# Run specific categories only (e.g., just internships)
python linkedin_email_scraper.py --categories internship_searches

# Customize delays and scrolling
python linkedin_email_scraper.py \
  --categories internship_searches entry_level_searches \
  --max-scrolls 10 \
  --scroll-pause 2.5 \
  --category-delay 15 \
  --output hiring_emails.csv

# Search for people instead of content posts
python linkedin_email_scraper.py --search-type people
```

### Key improvements for reliability
- **Login retry logic**: Automatically retries login up to 3 times with exponential backoff on timeout
- **Sequential processing**: Processes one category at a time (no longer opens all tabs at once)
- **Continuous saving**: Saves results after **EVERY query** completes (maximum data preservation on crash)
- **Post expansion**: Automatically clicks "see more" buttons to expand truncated posts before extracting emails
- **Better error handling**: Continues to next query if one fails; shows detailed progress

### Recommended settings to avoid timeouts
```bash
# Conservative settings for maximum reliability
python linkedin_email_scraper.py \
  --max-scrolls 5 \
  --scroll-pause 3.0 \
  --tab-delay 4.0 \
  --category-delay 15.0
```

## Output

The script creates a CSV file (`emails.csv` by default) with the following columns:
- **email**: The extracted email address
- **category**: The query category (e.g., internship_searches)
- **query**: The specific search query that found this email
- **count**: Number of times this email appeared in results for this query

## Notes & Best practices
- Do not hardcode credentials in code. Use environment variables or interactive prompt.
- Be conservative with scrolls and pauses to avoid triggering anti-bot measures.
- Consider using a real browser (non-headless) to reduce detection likelihood.
- The script opens multiple tabs in one browser window - avoid closing tabs manually during execution.
- This script is a simple educational example. For production or heavy scraping, consider respectful rate-limiting and legal compliance.
