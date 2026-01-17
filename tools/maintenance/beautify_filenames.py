from src.utils import run_beautification, logger

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Beautify research paper library")
    parser.add_argument("--commit", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--db-path", type=str, help="Target a specific database file")
    args = parser.parse_args()
    
    is_dry = not args.commit
    if not is_dry:
        print("!!! RUNNING IN COMMIT MODE - FILES WILL BE RENAMED !!!")
    else:
        print("Running in DRY RUN mode. Use --commit to apply changes.")
        
    changes, errors = run_beautification(dry_run=is_dry, db_path=args.db_path)
    print(f"\nSummary: {changes} updated, {errors} errors.")
