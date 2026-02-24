import asyncio
import argparse

from .main import main



def get_args():
    # ArgumentParser object to capture command-line arguments
    parser = argparse.ArgumentParser(description="Crawl LinkedIn job listings")
    
    # Define the arguments
    parser.add_argument("--title", type=str, required=True, help="Job title")
    # parser.add_argument("--location", type=str, required=True, help="Job location")
    parser.add_argument("--data_name", type=str, required=True, help="Name for the output CSV file")
    parser.add_argument("--max_results", type=int, default=100, help="Max number of jobs to scrape (default: 100)")

    # Parse the arguments
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    asyncio.run(main(args.title, args.data_name, args.max_results))