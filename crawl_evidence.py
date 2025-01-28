import pandas as pd
import json
import os
import multiprocessing
import tldextract
from utils.webpage_crawler import WebpageProcessor
from ftlangdetect import detect
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

def crawl_claim_evidences(claim_id, claim_search_results):
    save_dir = "data/knowledge_store/"
    processor = WebpageProcessor()
    crawled_info = []
    print("Processing claim", claim_id)
    q_cnt = 0
    for query, page_results in claim_search_results.items():
        for page_num, results in page_results.items():
            for result in results:
                if should_filter_link(result["link"]):
                    continue
                try:
                    print(claim_id, "=>", result["link"])
                    page_json = processor.url2lines(result["link"], method="trafilatura")
                    if page_json is not None:
                        crawled_text = page_json["text"]
                        crawled_url = page_json["source"]
                    else:
                        crawled_text = ""
                        crawled_url = ""

                except Exception as e:
                    crawled_text = ""
                    crawled_url = ""

                crawled_info.append({
                    "claim_id": claim_id,
                    "query": query,
                    "page_num": page_num,
                    "url": result["link"],
                    "crawled_url": crawled_url,
                    "text": crawled_text
                })
        q_cnt += 1
        # print(claim_id, "=>", q_cnt)

    with open(os.path.join(save_dir, f"{claim_id}.json"), "w") as f:
        json.dump(crawled_info, f, indent=2)
    processor.cleanup()

def process_claims(df, search_results, max_claims, max_processes):
    save_dir = "data/knowledge_store/"

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    processed_claims = [f for f in os.listdir(save_dir) if f.endswith(".json")]
    processed_claims = [int(f.split(".")[0]) for f in processed_claims]
    print(len(processed_claims), " claims already processed")

    with multiprocessing.Pool(processes=max_processes) as pool:
        tasks = []
        for row in df.iterrows():
            claim_id = row[0]
            if claim_id in processed_claims:
                print(claim_id)
                continue

            # if claim_id > max_claims:
            #     break

            if claim_id not in [170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180]:
                continue

            # Do not process non-English claims
            claim_filtered = row[1].claim.replace("\n", " ")
            if detect(text=claim_filtered, low_memory=False)["lang"] != "en":
                print(f"Skipping claim {claim_id} because it is not in English")
                continue

            claim_search_results = search_results[row[1].claim]
            tasks.append((claim_id, claim_search_results))

        if tasks:
            pool.starmap(crawl_claim_evidences, tasks)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max_claims', type=int, default=1,
                       help='Maximum number of claims to process')
    parser.add_argument('--max_processes', type=int, default=6,
                       help='Maximum number of processes to use')
    args = parser.parse_args()

    df = pd.read_csv("data/fnd_politifact_claims_final.csv", encoding='utf-8')
    with open("data/search_results.json", "r") as f:
        search_results = json.load(f)
    process_claims(df, search_results, args.max_claims, args.max_processes)

if __name__ == "__main__":
    main()
