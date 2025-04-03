import pandas as pd
import json
import os
import multiprocessing
import tldextract
import signal
from utils.webpage_crawler import WebpageProcessor
import argparse

# Blacklists
BLACKLIST_DOMAINS = {
    "jstor.org",
    "facebook.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "linkedin.com",
    "threads.net",
    "quora.com",
    "tiktok.com",
    "instagram.com",
    "discord.com",
    "youtube.com",
    "spotify.com",
    "huggingface.co",
    "politifact.com",
    "snopes.com",
    "factcheck.org",
    "shutterstock.com",
    "naturepl.com",
    "example.com",
    "pinterest.com",
    "flickr.com",
    "twitch.tv",
    "verifythis.com",
    "telegram.org",
    "factcheck.africa",
    "washingtonpost.com",
    "reuters.com",
    "nytimes.com"
}

BLACKLIST_FILES = [
    "/glove.",
    "ftp://ftp.cs.princeton.edu/pub/cs226/autocomplete/words-333333.txt",
    "https://web.mit.edu/adamrose/Public/googlelist",
]

def get_domain_name(url):
    if '://' not in url:
        url = 'http://' + url
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"

def should_filter_link(link):
    domain = get_domain_name(link)
    if domain in BLACKLIST_DOMAINS:
        return True
    if any(b_file in link for b_file in BLACKLIST_FILES):
        print("Blacklisted file: ", link)
        return True
    if link.endswith((".txt")):
        print("Blacklisted file type: ", link)
        return True
    return False

def crawl_claim_evidences(claim_id, claim_search_results, timeout=45):
    save_dir = "data/knowledge_store/"
    processor = WebpageProcessor()
    crawled_info = []
    print("Processing claim", claim_id)
    
    class TimeoutException(Exception):
        pass
    
    def timeout_handler(signum, frame):
        print("Timeout!")
        raise TimeoutException("Function timed out")
    
    for query, page_results in claim_search_results.items():
        for page_num, results in page_results.items():
            for result in results:
                if should_filter_link(result["link"]):
                    continue
                try:
                    print(claim_id, "=>", result["link"])
                    # Set the timeout
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout)
                    
                    crawled_text = processor.url2lines(result["link"], method="auto")

                    # Cancel the alarm if the function completes
                    signal.alarm(0)
                except Exception as e:
                    print(e)
                    crawled_text = []

                crawled_info.append({
                    "claim_id": claim_id,
                    "query": query,
                    "page_num": page_num,
                    "url": result["link"],
                    "text": crawled_text
                })

    with open(os.path.join(save_dir, f"{claim_id}.json"), "w") as f:
        json.dump(crawled_info, f, indent=2)
    processor.cleanup()

def process_claims(dataset, search_results, max_processes):
    save_dir = "data/knowledge_store/"

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    processed_claims = [f for f in os.listdir(save_dir) if f.endswith(".json")]
    print(len(processed_claims), " claims already processed")

    with multiprocessing.Pool(processes=max_processes) as pool:
        tasks = []
        for ix, claim_object in enumerate(dataset):            
            claim_id = claim_object['claim_id']
            if f'{claim_id}.json' in processed_claims:
                print(claim_id, " already processed")
                continue

            claim_search_results = search_results[claim_object['claim']]
            tasks.append((claim_id, claim_search_results))

        if tasks:
            pool.starmap(crawl_claim_evidences, tasks)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max_processes', type=int, default=16,
                       help='Maximum number of processes to use')
    args = parser.parse_args()

    with open("data/dataset_politifact.json", "r") as f:
        dataset = json.load(f)

    with open("data/search_results.json", "r") as f:
        search_results = json.load(f)
    process_claims(dataset, search_results, args.max_processes)

if __name__ == "__main__":
    main()
