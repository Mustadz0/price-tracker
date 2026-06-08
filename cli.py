#!/usr/bin/env python3
"""
Competitor Price Tracker — CLI

Usage:
  python cli.py add https://example.com/product
  python cli.py list
  python cli.py check [--all]
  python cli.py history 1
  python cli.py alerts
  python cli.py delete 1
"""

import argparse
import sys
from datetime import datetime
from tabulate import tabulate

from core.database import PriceDB
from core.scraper import scrape


def cmd_add(args):
    db = PriceDB()
    result = scrape(args.url)
    if result:
        pid = db.add_product(args.url, result["title"])
        db.save_price(pid, result["price"])
        print(f"[OK] Added: {result['title'][:80]}")
        print(f"     Price: ${result['price']:.2f}")
    else:
        pid = db.add_product(args.url, args.url)
        print(f"[WARN] Added URL (could not scrape): {args.url}")
    print(f"     ID: {pid}")


def cmd_list(args):
    db = PriceDB()
    products = db.get_products()
    if not products:
        print("No products tracked. Use 'add' to add one.")
        return
    rows = []
    for p in products:
        latest = db.get_latest_price(p["id"])
        prev = db.get_previous_price(p["id"])
        change = ""
        if latest and prev and prev != 0:
            pct = ((latest - prev) / prev) * 100
            change = f"{pct:+.1f}%"
        rows.append([p["id"], p["name"][:50], f"${latest:.2f}" if latest else "?", change])
    print(tabulate(rows, headers=["ID", "Product", "Price", "Change"], tablefmt="simple"))


def cmd_check(args):
    db = PriceDB()
    products = db.get_products()
    if not products:
        print("No products to check.")
        return
    for p in products:
        print(f"  Checking: {p['name'][:60]}...", end=" ")
        result = scrape(p["url"])
        if not result:
            print("FAILED")
            continue
        old_price = db.get_latest_price(p["id"])
        db.save_price(p["id"], result["price"])
        if old_price and old_price != result["price"]:
            change = ((result["price"] - old_price) / old_price) * 100
            msg = f"Price changed: ${old_price:.2f} -> ${result['price']:.2f} ({change:+.1f}%)"
            db.record_alert(p["id"], old_price, result["price"], change, msg)
            print(f"${result['price']:.2f} ({change:+.1f}%)")
        else:
            print(f"${result['price']:.2f} (no change)")


def cmd_history(args):
    db = PriceDB()
    product = db.get_product(args.id)
    if not product:
        print(f"Product #{args.id} not found.")
        return
    print(f"History for: {product['name']}")
    history = db.get_price_history(args.id)
    rows = []
    for h in history:
        rows.append([h["checked_at"][:19], f"${h['price']:.2f}", h["currency"]])
    print(tabulate(rows, headers=["Date", "Price", "Currency"], tablefmt="simple"))


def cmd_alerts(args):
    db = PriceDB()
    alerts = db.get_alerts()
    if not alerts:
        print("No price alerts yet.")
        return
    rows = []
    for a in alerts:
        rows.append([
            a["created_at"][:19],
            a["product_name"][:40],
            f"${a['old_price']:.2f}" if a["old_price"] else "?",
            f"${a['new_price']:.2f}" if a["new_price"] else "?",
            f"{a['change_pct']:+.1f}%" if a["change_pct"] else "",
        ])
    print(tabulate(rows, headers=["Date", "Product", "Old", "New", "Change"], tablefmt="simple"))


def cmd_delete(args):
    db = PriceDB()
    db.delete_product(args.id)
    print(f"Deleted product #{args.id}")


def main():
    ap = argparse.ArgumentParser(
        description="Competitor Price Tracker",
        epilog="""
Commands:
  add URL      Track a new product URL
  list         Show all tracked products
  check        Check latest prices
  history ID   Show price history for a product
  alerts       Show recent price alerts
  delete ID    Remove a product
        """,
    )
    ap.add_argument("command", choices=["add", "list", "check", "history", "alerts", "delete"])
    ap.add_argument("url", nargs="?", help="Product URL (for add)")
    ap.add_argument("id", nargs="?", type=int, help="Product ID")

    args = ap.parse_args()

    if args.command == "add":
        if not args.url:
            print("Usage: python cli.py add <url>")
            sys.exit(1)
        cmd_add(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "history":
        if not args.id:
            print("Usage: python cli.py history <id>")
            sys.exit(1)
        cmd_history(args)
    elif args.command == "alerts":
        cmd_alerts(args)
    elif args.command == "delete":
        if not args.id:
            print("Usage: python cli.py delete <id>")
            sys.exit(1)
        cmd_delete(args)


if __name__ == "__main__":
    main()
