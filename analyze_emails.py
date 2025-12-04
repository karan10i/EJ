#!/usr/bin/env python3
"""
Analyze mail.csv to show email counts by category and query.

Usage:
    python analyze_emails.py
    python analyze_emails.py --csv mail.csv
    python analyze_emails.py --csv mail.csv --date 2025-11-17
"""

import csv
import argparse
from collections import defaultdict
from typing import Dict, List


def analyze_by_category(csv_path: str, filter_date: str = None) -> Dict[str, int]:
    """Count emails by category."""
    category_counts = defaultdict(int)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get('date') or '').strip()
            if filter_date and date != filter_date:
                continue
            
            category = (row.get('category') or 'Unknown').strip()
            category_counts[category] += 1
    
    return dict(category_counts)


def analyze_by_query(csv_path: str, filter_date: str = None) -> Dict[str, Dict[str, int]]:
    """Count emails by category and query."""
    query_counts = defaultdict(lambda: defaultdict(int))
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get('date') or '').strip()
            if filter_date and date != filter_date:
                continue
            
            category = (row.get('category') or 'Unknown').strip()
            query = (row.get('query') or 'Unknown').strip()
            query_counts[category][query] += 1
    
    return {cat: dict(queries) for cat, queries in query_counts.items()}


def count_unique_emails(csv_path: str, filter_date: str = None) -> int:
    """Count unique email addresses."""
    unique_emails = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get('date') or '').strip()
            if filter_date and date != filter_date:
                continue
            
            email = (row.get('email') or '').strip().lower()
            if email:
                unique_emails.add(email)
    
    return len(unique_emails)


def list_available_dates(csv_path: str) -> List[str]:
    """List all unique dates in the CSV."""
    dates = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get('date') or '').strip()
            if date:
                dates.add(date)
    
    return sorted(dates)


def main():
    parser = argparse.ArgumentParser(description='Analyze email counts by category and query')
    parser.add_argument('--csv', default='mail.csv', help='Path to CSV file')
    parser.add_argument('--date', type=str, default=None, help='Filter by specific date (YYYY-MM-DD)')
    parser.add_argument('--list-dates', action='store_true', help='List all available dates and exit')
    parser.add_argument('--detailed', action='store_true', help='Show per-query breakdown')
    args = parser.parse_args()
    
    # List dates and exit if requested
    if args.list_dates:
        dates = list_available_dates(args.csv)
        print(f"\n📅 Available dates in {args.csv}:")
        for date in dates:
            print(f"  - {date}")
        return
    
    # Header
    print(f"\n{'='*60}")
    print(f"📊 Email Analysis: {args.csv}")
    if args.date:
        print(f"🗓️  Filtered by date: {args.date}")
    print(f"{'='*60}\n")
    
    # Unique email count
    unique_count = count_unique_emails(args.csv, args.date)
    print(f"📧 Total unique emails: {unique_count}\n")
    
    # Category breakdown
    category_counts = analyze_by_category(args.csv, args.date)
    print(f"📂 Emails by Category:")
    print(f"{'-'*60}")
    
    total = sum(category_counts.values())
    for category in sorted(category_counts.keys()):
        count = category_counts[category]
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {category:30} {count:5} ({percentage:5.1f}%)")
    
    print(f"{'-'*60}")
    print(f"  {'TOTAL':30} {total:5}\n")
    
    # Detailed query breakdown if requested
    if args.detailed:
        query_counts = analyze_by_query(args.csv, args.date)
        print(f"🔍 Detailed breakdown by query:")
        print(f"{'='*60}\n")
        
        for category in sorted(query_counts.keys()):
            print(f"📁 {category}")
            print(f"{'-'*60}")
            queries = query_counts[category]
            for query in sorted(queries.keys(), key=lambda q: queries[q], reverse=True):
                count = queries[query]
                print(f"  {query:45} {count:5}")
            print(f"{'-'*60}")
            print(f"  {'Subtotal':45} {sum(queries.values()):5}\n")


if __name__ == '__main__':
    main()
