import argparse
import sys

# We add the project directory to the path to ensure sibling imports work
# This is a good practice for making your project structure robust.
sys.path.append('.')

# Import the main functions from your workers
from workers.ingest_worker import run_ingestion_worker
from workers.enrichment_worker import run_enrichment_worker
from workers.verification_worker import run_verification_worker

def main():
    """Main entry point for the data pipeline CLI."""
    parser = argparse.ArgumentParser(description="Fency Outreach Data Pipeline CLI")
    
    # Define the commands for the CLI
    parser.add_argument(
        "worker",
        choices=['ingest', 'enrich', 'verify'],
        help="The name of the worker to run."
    )
    
    args = parser.parse_args()

    print(f"--- Fency Outreach Pipeline: Starting '{args.worker}' worker ---")

    if args.worker == 'ingest':
        run_ingestion_worker()
    elif args.worker == 'enrich':
        run_enrichment_worker()
    elif args.worker == 'verify':
        run_verification_worker()
    else:
        print(f"Unknown worker: {args.worker}")
        sys.exit(1)
        
    print(f"--- Worker '{args.worker}' finished or was stopped. ---")

if __name__ == "__main__":
    main()