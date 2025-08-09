#!/usr/bin/env python3
"""
Product Issues Summary Generator

This script generates a comprehensive summary of all product issues found during scraping,
including name mismatches, 404 errors, and other scraping problems.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import DatabaseManager, DatabaseConfig


def generate_issues_summary(auto_handle=False):
    """Generate a comprehensive summary of all product issues."""

    print("🔍 Product Issues Summary Generator")
    print("=" * 50)

    # Initialize database
    config = DatabaseConfig.from_config_file("database.conf")
    db_manager = DatabaseManager(config)

    if config.database_type != "sqlite":
        print("❌ This tool only works with SQLite database mode.")
        print("Please set database_type=sqlite in database.conf")
        return

    # Auto-handle critical issues if requested
    if auto_handle:
        print("🤖 Auto-handling critical issues...")
        handled_count = db_manager.auto_handle_critical_issues(auto_remove=True)
        if handled_count > 0:
            print(f"✅ Auto-handled {handled_count} critical issues")
        else:
            print("ℹ️  No critical issues to auto-handle")
        print()

    # Get all unresolved issues
    issues = db_manager.get_product_issues(resolved=False)

    if not issues:
        print("✅ No unresolved product issues found!")
        return

    print(f"Found {len(issues)} unresolved issues:\n")

    # Group issues by type
    issues_by_type = {}
    for issue in issues:
        issue_type = issue["issue_type"]
        if issue_type not in issues_by_type:
            issues_by_type[issue_type] = []
        issues_by_type[issue_type].append(issue)

    # Generate summary by issue type
    urls_to_fix = []

    for issue_type, type_issues in issues_by_type.items():
        print(f"\n📋 {issue_type.upper().replace('_', ' ')} ({len(type_issues)} issues)")
        print("-" * 40)

        for issue in type_issues:
            product_name = issue["product_name"]
            url = issue["url"]
            detected_at = issue["detected_at"]

            print(f"  🔴 Product: {product_name}")
            print(f"     URL: {url}")
            print(f"     Detected: {detected_at}")

            if issue_type == "name_mismatch":
                if issue["expected_name"]:
                    print(f"     Expected: {issue['expected_name']}")
                if issue["actual_name"]:
                    print(f"     Found: {issue['actual_name']}")

            if issue["error_message"]:
                print(f"     Error: {issue['error_message']}")

            if issue["http_status_code"]:
                print(f"     HTTP Status: {issue['http_status_code']}")

            # Add to fix list
            urls_to_fix.append(
                {
                    "product_name": product_name,
                    "url": url,
                    "issue_type": issue_type,
                    "error": (
                        issue["error_message"] or f"{issue['http_status_code']}"
                        if issue["http_status_code"]
                        else "Unknown"
                    ),
                }
            )

            print()

    # Guidance for JSON maintenance
    print("\n" + "=" * 50)
    print("📝 RECOMMENDED ACTIONS FOR products.json")
    print("=" * 50)

    print("\nReview these URLs in products.json (remove, update, or deactivate via DB):")
    print("-" * 40)
    for fix in urls_to_fix:
        issue_type = fix["issue_type"]
        if issue_type == "404_error":
            action = "❌ REMOVE URL (404)"
        elif issue_type == "name_mismatch":
            action = "⚠️  UPDATE URL (Wrong Product Content)"
        elif issue_type == "scrape_error":
            action = "🔧 INVESTIGATE SELECTORS"
        elif issue_type == "anti_bot":
            action = "🤖 RETRY LATER (Anti-bot)"
        else:
            action = "🔍 INVESTIGATE"
        print(
            f"{action}\n  Product: {fix['product_name']}\n  URL: {fix['url']}\n  Issue: {fix['error']}\n"
        )

    print(
        "\nIf removing URLs, update products.json then run main to sync (non-destructive add only). For deactivation use DatabaseManager.deactivate_product_url()."
    )

    # Summary statistics
    print("\n" + "=" * 50)
    print("📊 SUMMARY STATISTICS")
    print("=" * 50)

    total_issues = len(issues)
    critical_issues = len([i for i in issues if i["issue_type"] in ["404_error", "name_mismatch"]])

    print(f"Total Issues: {total_issues}")
    print(f"Critical Issues (404/Name Mismatch): {critical_issues}")
    print(f"Other Issues: {total_issues - critical_issues}")

    # Show issue breakdown
    print(f"\nIssue Breakdown:")
    for issue_type, count in sorted([(k, len(v)) for k, v in issues_by_type.items()]):
        print(f"  {issue_type.replace('_', ' ').title()}: {count}")

    print(f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        "\n💡 TIP: After editing products.json, run the scraper to import new URLs (removals must be handled manually if desired)."
    )


if __name__ == "__main__":
    try:
        import sys

        auto_handle = "--auto-handle" in sys.argv
        if auto_handle:
            print("🤖 Auto-handling mode enabled")
        generate_issues_summary(auto_handle=auto_handle)
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        sys.exit(1)
