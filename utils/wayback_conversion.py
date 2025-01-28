from waybackpy import WaybackMachineSaveAPI, WaybackMachineCDXServerAPI

# Replace with the URL you want to check and save
url = "https://www.bbc.com/news/world-us-canada-69028127"
user_agent = "Mozilla/5.0 (compatible; Waybackpy/3.0.6)"

# Initialize the CDX Server API to check for existing archives
cdx_api = WaybackMachineCDXServerAPI(url, user_agent)

# Attempt to retrieve the most recent archive
try:
    newest_archive = cdx_api.oldest()
    archive_url = newest_archive.archive_url
    print(f"Most recent archive: {archive_url}")
except Exception as e:
    print("No existing archive found. Proceeding to save the page.")
    # Initialize the Save API to save the page
    save_api = WaybackMachineSaveAPI(url, user_agent)
    archive_url = save_api.save()
    print(f"New archive created: {archive_url}")