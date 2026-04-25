import argparse

from src.scraper import flush_buffered_snapshots, scrape_and_store

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--flush-only", action="store_true", help="Replay buffered snapshots without scraping a new one")
    args = parser.parse_args()

    if args.flush_only:
        inserted, remaining = flush_buffered_snapshots()
        print(f"Flush complete: inserted={inserted}, remaining={remaining}")
    else:
        scrape_and_store()
