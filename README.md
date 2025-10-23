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

# run all queries from search_queries.json (default: content search)
python linkedin_email_scraper.py

# run specific categories only
python linkedin_email_scraper.py --categories internship_searches entry_level_searches

# customize search type (content/people/jobs)
python linkedin_email_scraper.py --search-type content --max-scrolls 10

# full example with all options
python linkedin_email_scraper.py \
  --queries search_queries.json \
  --categories internship_searches \
  --search-type content \
  --max-scrolls 5 \
  --scroll-pause 2.5 \
  --tab-delay 2.0 \
  --output internship_emails.csv
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
