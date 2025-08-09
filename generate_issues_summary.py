#!/usr/bin/env python3
"""
Product Issues Summary Generator

This script generates a comprehensive summary of all product issues found during scraping,
including name mismatches, 404 errors, and other scraping problems.
"""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Dict, List, Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import DatabaseManager, DatabaseConfig


# ---------------------------- Data Structures ----------------------------- #


@dataclass(slots=True)
class Issue:
    product_name: str
    url: str
    issue_type: str
    detected_at: str
    expected_name: str | None = None
    actual_name: str | None = None
    error_message: str | None = None
    http_status_code: int | None = None

    @property
    def is_critical(self) -> bool:
        return self.issue_type in {"404_error", "name_mismatch"}

    @property
    def short_error(self) -> str:
        if self.error_message:
            return self.error_message
        if self.http_status_code:
            return str(self.http_status_code)
        return "Unknown"


# ------------------------------ Helpers ---------------------------------- #


def _group_by_type(issues: Iterable[Issue]) -> Dict[str, List[Issue]]:
    grouped: Dict[str, List[Issue]] = {}
    for issue in issues:
        grouped.setdefault(issue.issue_type, []).append(issue)
    return grouped


def _load_issues(db_manager: DatabaseManager) -> List[Issue]:
    raw = db_manager.get_product_issues(resolved=False)
    return [
        Issue(
            product_name=i.get("product_name"),
            url=i.get("url"),
            issue_type=i.get("issue_type"),
            detected_at=i.get("detected_at"),
            expected_name=i.get("expected_name"),
            actual_name=i.get("actual_name"),
            error_message=i.get("error_message"),
            http_status_code=i.get("http_status_code"),
        )
        for i in raw
    ]


ACTION_LABELS = {
    "404_error": "❌ REMOVE URL (404)",
    "name_mismatch": "⚠️  UPDATE URL (Wrong Product Content)",
    "scrape_error": "🔧 INVESTIGATE SELECTORS",
    "anti_bot": "🤖 RETRY LATER (Anti-bot)",
}


def _action_for(issue_type: str) -> str:
    return ACTION_LABELS.get(issue_type, "🔍 INVESTIGATE")


def _print_issue_group(issue_type: str, items: List[Issue], urls_to_fix: List[Dict[str, Any]]):
    print(f"\n📋 {issue_type.upper().replace('_', ' ')} ({len(items)} issues)")
    print("-" * 40)
    for issue in items:
        print(f"  🔴 Product: {issue.product_name}")
        print(f"     URL: {issue.url}")
        print(f"     Detected: {issue.detected_at}")
        if issue.issue_type == "name_mismatch":
            if issue.expected_name:
                print(f"     Expected: {issue.expected_name}")
            if issue.actual_name:
                print(f"     Found: {issue.actual_name}")
        if issue.error_message:
            print(f"     Error: {issue.error_message}")
        if issue.http_status_code:
            print(f"     HTTP Status: {issue.http_status_code}")
        urls_to_fix.append(
            {
                "product_name": issue.product_name,
                "url": issue.url,
                "issue_type": issue.issue_type,
                "error": issue.short_error,
            }
        )
        print()


def _print_recommended_actions(urls_to_fix: List[Dict[str, Any]]):
    print("\n" + "=" * 50)
    print("📝 RECOMMENDED ACTIONS FOR products.json")
    print("=" * 50)
    print("\nReview these URLs in products.json (remove, update, or deactivate via DB):")
    print("-" * 40)
    for fix in urls_to_fix:
        action = _action_for(fix["issue_type"])
        print(
            f"{action}\n  Product: {fix['product_name']}\n  URL: {fix['url']}\n  Issue: {fix['error']}\n"
        )
    print(
        "\nIf removing URLs, update products.json then run main to sync (non-destructive add only). For deactivation use DatabaseManager.deactivate_product_url()."
    )


def _print_summary_stats(issues: List[Issue], issues_by_type: Dict[str, List[Issue]]):
    print("\n" + "=" * 50)
    print("📊 SUMMARY STATISTICS")
    print("=" * 50)
    total = len(issues)
    critical = sum(1 for i in issues if i.is_critical)
    print(f"Total Issues: {total}")
    print(f"Critical Issues (404/Name Mismatch): {critical}")
    print(f"Other Issues: {total - critical}")
    print("\nIssue Breakdown:")
    for issue_type, group in sorted(issues_by_type.items()):
        print(f"  {issue_type.replace('_', ' ').title()}: {len(group)}")
    print(f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        "\n💡 TIP: After editing products.json, run the scraper to import new URLs (removals must be handled manually if desired)."
    )


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
    issues = _load_issues(db_manager)

    if not issues:
        print("✅ No unresolved product issues found!")
        return
    print(f"Found {len(issues)} unresolved issues:\n")
    issues_by_type = _group_by_type(issues)
    urls_to_fix: List[Dict[str, Any]] = []
    for issue_type, items in issues_by_type.items():
        _print_issue_group(issue_type, items, urls_to_fix)
    _print_recommended_actions(urls_to_fix)
    _print_summary_stats(issues, issues_by_type)


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
