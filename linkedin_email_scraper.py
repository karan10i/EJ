"""
LinkedIn multi-query email scraper

This script uses Selenium to log in to LinkedIn, run multiple search queries across different
hiring categories (internships, entry-level, open-source), open each search in a separate tab
within one browser window, scrape all visible posts, extract emails using regex, and save
unique emails to a CSV with query/category metadata.

Notes:
- Do NOT hardcode credentials. Use environment variables or interactive prompt.
- Respect LinkedIn's terms of service and robots.txt: this script is for educational/personal use only.

Usage:
    python linkedin_email_scraper.py --queries search_queries.json --categories internship_searches entry_level_searches

"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import re
import time
import csv
import os
import argparse
import getpass
import json
import urllib.parse

# Regex pattern to match email addresses
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def get_credentials():
    """Get LinkedIn credentials from env or prompt securely."""
    username = os.environ.get("LINKEDIN_USERNAME")
    password = os.environ.get("LINKEDIN_PASSWORD")
    if username and password:
        print("Using credentials from environment variables.")
        return username, password

    # Prompt the user securely
    username = input("LinkedIn username (email): ").strip()
    password = getpass.getpass("LinkedIn password: ")
    return username, password


def init_driver(headless=False):
    """Initialize Selenium webdriver (Chrome) using webdriver-manager."""
    options = webdriver.ChromeOptions()
    # Run in headful mode by default to avoid detection; headless can be enabled via arg
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    # Some common options to make automation reliable
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,900")
    # Optionally disable automation flags
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        # webdriver.Chrome no longer accepts the driver path as a positional arg together with options
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except WebDriverException as e:
        print("Failed to start Chrome webdriver:", e)
        raise

    # Basic anti-detection JS (still not bulletproof)
    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )

    return driver


def login_linkedin(driver, username, password, wait_time=10, max_retries=3):
    """Log in to LinkedIn using provided credentials with retry logic.

    Args:
        driver: Selenium webdriver
        username: LinkedIn username/email
        password: LinkedIn password
        wait_time: Seconds to wait for elements
        max_retries: Number of login attempts before giving up

    Returns True on success, False otherwise.
    """
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Login attempt {attempt}/{max_retries}...")
            driver.get("https://www.linkedin.com/login")
            wait = WebDriverWait(driver, wait_time)

            # Wait for username and password fields
            email_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
            pass_input = driver.find_element(By.ID, "password")

            email_input.clear()
            email_input.send_keys(username)
            pass_input.clear()
            pass_input.send_keys(password)

            # Submit the form
            pass_input.send_keys(Keys.RETURN)

            # Wait for navigation - presence of profile nav as success indicator
            wait.until(EC.presence_of_element_located((By.ID, "global-nav-search")))
            print("✓ Logged in successfully.")
            return True
            
        except TimeoutException:
            print(f"✗ Login timeout on attempt {attempt}")
            if attempt < max_retries:
                wait_seconds = attempt * 5  # Exponential backoff
                print(f"  Waiting {wait_seconds}s before retry...")
                time.sleep(wait_seconds)
            else:
                print("Login failed after all retries. Check credentials or try again later.")
                return False
                
        except Exception as e:
            print(f"✗ Unexpected error during login attempt {attempt}: {e}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                return False
    
    return False


def scroll_and_collect(driver, scroll_pause=2.0, max_scrolls=10):
    """Scroll the feed to load posts and collect page HTML after each scroll.
    
    Also attempts to expand truncated posts by clicking "see more" buttons.

    Returns concatenated HTML of loaded content.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    html_chunks = []

    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        
        # Try to expand truncated posts by clicking "see more" buttons
        try:
            # LinkedIn uses various text for expansion: "...more", "see more", etc.
            see_more_buttons = driver.find_elements(By.XPATH, 
                "//*[contains(@class, 'see-more') or contains(@class, 'show-more') or "
                "contains(text(), '...more') or contains(text(), 'see more') or "
                "contains(text(), 'See more')]")
            
            clicked = 0
            for btn in see_more_buttons[:10]:  # Limit to 10 per scroll to avoid infinite loops
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", btn)
                        clicked += 1
                        time.sleep(0.2)
                except:
                    continue
            
            if clicked > 0:
                print(f"  → Expanded {clicked} truncated posts")
                time.sleep(1)  # Give time for content to load
        except Exception as e:
            # Silent failure - expansion is best-effort
            pass
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        # Collect current page HTML
        html_chunks.append(driver.page_source)
        print(f"Scrolled {i+1}/{max_scrolls}")
        
        if new_height == last_height:
            # Reached the bottom or no more dynamic content
            break
        last_height = new_height

    return "\n".join(html_chunks)


def extract_posts_from_html(html):
    """Parse HTML with BeautifulSoup to extract textual content of posts.

    Returns a list of strings (post texts).
    """
    soup = BeautifulSoup(html, "html.parser")
    posts = []

    # LinkedIn posts commonly use <div> elements with data-urn attributes or role="article"
    # Find elements that look like posts
    article_selectors = soup.find_all(lambda tag: tag.name == 'div' and tag.get('role') == 'article')
    if not article_selectors:
        # Fallback: search for divs with data-urn or feed-shared-update
        article_selectors = soup.find_all('div', attrs={'data-urn': True})

    for art in article_selectors:
        # Get visible text
        text = art.get_text(separator=' ', strip=True)
        if text:
            posts.append(text)

    # Deduplicate posts while preserving order
    seen = set()
    unique_posts = []
    for p in posts:
        if p not in seen:
            seen.add(p)
            unique_posts.append(p)

    return unique_posts


def load_search_queries(json_path, categories=None):
    """Load search queries from a JSON file and filter by categories if provided.
    
    Args:
        json_path: Path to JSON file with query categories
        categories: List of category names to include (None = all categories)
    
    Returns:
        Dict mapping category names to lists of search queries
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        all_queries = json.load(f)
    
    if categories:
        # Filter to only requested categories
        filtered = {cat: all_queries[cat] for cat in categories if cat in all_queries}
        return filtered
    return all_queries


def build_linkedin_search_url(query, search_type='content'):
    """Build a LinkedIn search URL for the given query.
    
    Args:
        query: Search term
        search_type: 'content' for posts, 'people' for profiles, 'jobs' for job listings
    
    Returns:
        Full LinkedIn search URL
    """
    base_urls = {
        'content': 'https://www.linkedin.com/search/results/content/',
        'people': 'https://www.linkedin.com/search/results/people/',
        'jobs': 'https://www.linkedin.com/search/results/jobs/'
    }
    base = base_urls.get(search_type, base_urls['content'])
    # Encode the query and add common filters
    params = {
        'keywords': query,
        'origin': 'FACETED_SEARCH'
    }
    query_string = urllib.parse.urlencode(params)
    return f"{base}?{query_string}"


def open_search_tabs(driver, queries_by_category, search_type='content', tab_delay=2):
    """Open multiple LinkedIn search tabs in the same browser window.
    
    Args:
        driver: Selenium webdriver instance
        queries_by_category: Dict mapping category names to query lists
        search_type: Type of LinkedIn search ('content', 'people', 'jobs')
        tab_delay: Seconds to wait between opening tabs
    
    Returns:
        List of dicts with 'category', 'query', 'url', 'handle' for each tab
    """
    tab_info = []
    first_tab = True
    
    for category, queries in queries_by_category.items():
        for query in queries:
            url = build_linkedin_search_url(query, search_type)
            
            if first_tab:
                # Use the current tab for the first query
                driver.get(url)
                handle = driver.current_window_handle
                first_tab = False
            else:
                # Open new tab with JavaScript
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
                driver.get(url)
                handle = driver.current_window_handle
            
            tab_info.append({
                'category': category,
                'query': query,
                'url': url,
                'handle': handle
            })
            
            print(f"Opened tab: [{category}] {query}")
            time.sleep(tab_delay)
    
    return tab_info


def scrape_tab(driver, tab_info, scroll_pause=2.0, max_scrolls=5):
    """Switch to a specific tab, scroll and collect posts.
    
    Args:
        driver: Selenium webdriver
        tab_info: Dict with tab metadata (handle, category, query, etc.)
        scroll_pause: Seconds between scrolls
        max_scrolls: Maximum scroll iterations
    
    Returns:
        List of post texts extracted from the tab
    """
    driver.switch_to.window(tab_info['handle'])
    print(f"\nScraping: [{tab_info['category']}] {tab_info['query']}")
    
    # Wait for content to load
    time.sleep(2)
    
    html = scroll_and_collect(driver, scroll_pause=scroll_pause, max_scrolls=max_scrolls)
    posts = extract_posts_from_html(html)
    print(f"  → Found {len(posts)} posts")
    
    return posts
    """Use regex to find unique email addresses in the provided texts."""
    found = set()
    for t in texts:
        for m in EMAIL_REGEX.findall(t):
            found.add(m.lower())
    return sorted(found)


    return posts


def find_emails_in_texts(texts):
    """Use regex to find unique email addresses in the provided texts."""
    found = set()
    for t in texts:
        for m in EMAIL_REGEX.findall(t):
            found.add(m.lower())
    return sorted(found)


def save_emails_to_csv(emails_with_metadata, output_path='emails.csv', mode='w'):
    """Save emails to CSV with query/category metadata.
    
    Args:
        emails_with_metadata: List of dicts with keys 'email', 'category', 'query'
        output_path: Output CSV file path
        mode: File mode ('w' for overwrite, 'a' for append)
    """
    file_exists = os.path.exists(output_path) and mode == 'a'
    
    with open(output_path, mode, newline='', encoding='utf-8') as csvfile:
        fieldnames = ['email', 'category', 'query', 'count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists or mode == 'w':
            writer.writeheader()
        
        # Aggregate emails by (email, category, query) and count occurrences
        email_counts = {}
        for item in emails_with_metadata:
            key = (item['email'], item['category'], item['query'])
            email_counts[key] = email_counts.get(key, 0) + 1
        
        for (email, category, query), count in sorted(email_counts.items()):
            writer.writerow({
                'email': email,
                'category': category,
                'query': query,
                'count': count
            })
    
    unique_emails = len(set(item['email'] for item in emails_with_metadata))
    print(f"  → Saved {unique_emails} unique emails ({len(emails_with_metadata)} total) to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='LinkedIn multi-query email scraper')
    parser.add_argument('--queries', type=str, default='search_queries.json', 
                        help='Path to JSON file with search queries')
    parser.add_argument('--categories', nargs='+', 
                        help='Specific categories to search (default: all)')
    parser.add_argument('--search-type', choices=['content', 'people', 'jobs'], default='content',
                        help='Type of LinkedIn search to perform')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--max-scrolls', type=int, default=5, 
                        help='Maximum number of scroll iterations per tab')
    parser.add_argument('--scroll-pause', type=float, default=2.0, 
                        help='Seconds to wait between scrolls')
    parser.add_argument('--tab-delay', type=float, default=3.0,
                        help='Seconds to wait between opening tabs')
    parser.add_argument('--category-delay', type=float, default=10.0,
                        help='Seconds to wait between processing categories')
    parser.add_argument('--output', type=str, default='emails.csv', help='Output CSV file path')
    parser.add_argument('--process-one-at-a-time', action='store_true',
                        help='Process one category at a time (slower but more reliable)')
    args = parser.parse_args()

    # Load search queries from JSON
    try:
        queries_by_category = load_search_queries(args.queries, args.categories)
        total_queries = sum(len(queries) for queries in queries_by_category.values())
        print(f"Loaded {total_queries} queries across {len(queries_by_category)} categories")
        print(f"Categories: {', '.join(queries_by_category.keys())}")
    except FileNotFoundError:
        print(f"Error: Could not find queries file: {args.queries}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {args.queries}")
        return

    username, password = get_credentials()

    driver = init_driver(headless=args.headless)
    
    try:
        success = login_linkedin(driver, username, password, max_retries=3)
        if not success:
            print('Login failed; exiting.')
            return

        # Process categories one at a time for reliability
        print(f"\n{'='*60}")
        print("Processing categories one at a time for maximum reliability")
        print(f"{'='*60}")
        
        # Clear output file at start
        if os.path.exists(args.output):
            print(f"Removing existing {args.output}")
            os.remove(args.output)
        
        for category_idx, (category, queries) in enumerate(queries_by_category.items(), 1):
            print(f"\n{'='*60}")
            print(f"[{category_idx}/{len(queries_by_category)}] Processing category: {category}")
            print(f"  Queries: {len(queries)}")
            print(f"{'='*60}")
            
            # Process each query in this category
            for query_idx, query in enumerate(queries, 1):
                try:
                    print(f"\n[{query_idx}/{len(queries)}] Query: {query}")
                    url = build_linkedin_search_url(query, args.search_type)
                    
                    # Navigate to search URL
                    driver.get(url)
                    time.sleep(args.tab_delay)
                    
                    # Scrape this page
                    html = scroll_and_collect(driver, 
                                             scroll_pause=args.scroll_pause, 
                                             max_scrolls=args.max_scrolls)
                    posts = extract_posts_from_html(html)
                    emails = find_emails_in_texts(posts)
                    
                    print(f"  → Found {len(posts)} posts, {len(emails)} emails")
                    
                    # Build email metadata for this query
                    query_emails = []
                    for email in emails:
                        query_emails.append({
                            'email': email,
                            'category': category,
                            'query': query
                        })
                    
                    # CONTINUOUS SAVE: Save after each query (append mode)
                    if query_emails:
                        # First query of first category = write mode, otherwise append
                        is_first = (category_idx == 1 and query_idx == 1)
                        mode = 'w' if is_first else 'a'
                        save_emails_to_csv(query_emails, output_path=args.output, mode=mode)
                    
                except Exception as e:
                    print(f"  ✗ Error processing query '{query}': {e}")
                    continue
            
            # Wait before next category
            if category_idx < len(queries_by_category):
                print(f"\n⏸  Waiting {args.category_delay}s before next category...")
                time.sleep(args.category_delay)
        
        print(f"\n{'='*60}")
        print(f"✓ All categories processed! Results saved to: {args.output}")
        print(f"{'='*60}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Partial results may be saved.")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        driver.quit()


if __name__ == '__main__':
    main()
