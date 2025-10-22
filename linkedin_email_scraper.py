"""
LinkedIn feed/email scraper

This script uses Selenium to log in to LinkedIn, navigate to the feed or a specific post URL,
collect visible post contents, extract emails using regex, and save unique emails to a CSV.

Notes:
- Do NOT hardcode credentials. Use environment variables or interactive prompt.
- Respect LinkedIn's terms of service and robots.txt: this script is for educational/personal use only.

Usage:
    python linkedin_email_scraper.py --url <optional_post_or_feed_url>

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


def login_linkedin(driver, username, password, wait_time=10):
    """Log in to LinkedIn using provided credentials.

    Returns True on success, False otherwise.
    """
    driver.get("https://www.linkedin.com/login")
    wait = WebDriverWait(driver, wait_time)

    try:
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
        print("Logged in successfully.")
        return True
    except TimeoutException:
        print("Login timeout or login elements not found. Check credentials or page structure.")
        return False
    except Exception as e:
        print("Unexpected error during login:", e)
        return False


def scroll_and_collect(driver, scroll_pause=2.0, max_scrolls=10):
    """Scroll the feed to load posts and collect page HTML after each scroll.

    Returns concatenated HTML of loaded content.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    html_chunks = []

    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
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


def find_emails_in_texts(texts):
    """Use regex to find unique email addresses in the provided texts."""
    found = set()
    for t in texts:
        for m in EMAIL_REGEX.findall(t):
            found.add(m.lower())
    return sorted(found)


def save_emails_to_csv(emails, output_path='emails.csv'):
    """Save unique emails to a CSV file, one per row."""
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['email'])
        for e in emails:
            writer.writerow([e])
    print(f"Saved {len(emails)} unique emails to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='LinkedIn email scraper')
    parser.add_argument('--url', help='Optional LinkedIn feed or post URL to open', default='https://www.linkedin.com/search/results/content/?datePosted=%22past-24h%22&keywords=software%20engineer%20hiring&origin=FACETED_SEARCH&sid=P5Z')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--max-scrolls', type=int, default=15, help='Maximum number of scroll iterations')
    parser.add_argument('--scroll-pause', type=float, default=2.0, help='Seconds to wait between scrolls')
    parser.add_argument('--output', type=str, default='emails.csv', help='Output CSV file path')
    args = parser.parse_args()

    username, password = get_credentials()

    driver = init_driver(headless=args.headless)
    try:
        success = login_linkedin(driver, username, password)
        if not success:
            print('Login failed; exiting.')
            return

        # Navigate to the provided URL (feed or specific post)
        print(f"Navigating to {args.url}")
        driver.get(args.url)
        # Give the page some time to load initial content
        time.sleep(3)

        html = scroll_and_collect(driver, scroll_pause=args.scroll_pause, max_scrolls=args.max_scrolls)
        posts = extract_posts_from_html(html)
        print(f"Found {len(posts)} posts (unique)")

        emails = find_emails_in_texts(posts)
        save_emails_to_csv(emails, output_path=args.output)

    finally:
        driver.quit()


if __name__ == '__main__':
    main()
