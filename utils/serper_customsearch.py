import requests
import json
from itertools import cycle

class SerperCustomSearch:
    def __init__(self, secrets_file):
        self.serper_api_counter = 0
        self.serper_url = "https://google.serper.dev/search"
        self.secrets_file = secrets_file
        self.keys_pool = self._load_secrets(self.secrets_file)
        self._rotate_secret() # Initialize the first secret

    def _load_secrets(self, secrets_file):
        with open(secrets_file) as fp:
            serper_api_secrets = json.load(fp)
        return cycle(serper_api_secrets)
    
    def _rotate_secret(self):
        # Keep rotating until we find a secret with available calls
        while True:
            current_secret = next(self.keys_pool)
            if current_secret["remaining_requests"] > 0:
                self.api_key = current_secret["api_key"]
                self.max_calls = current_secret["remaining_requests"]
                self.request_counter = 0
                print("Changed Serper search SECRET, ", self.max_calls, " calls remaining")
                break
            print("Skipping depleted API key")

    def _update_secrets_file(self):
        # Read current secrets
        with open(self.secrets_file) as fp:
            secrets = json.load(fp)
        
        # Update the remaining_requests for current API key
        for secret in secrets:
            if secret["api_key"] == self.api_key:
                secret["remaining_requests"] = self.max_calls
                break
        
        # Write back to file
        with open(self.secrets_file, 'w') as fp:
            json.dump(secrets, fp, indent=4)
    
    # def _rotate_secret(self):
    #     current_secret = next(self.keys_pool)
    #     self.api_key = current_secret["api_key"]
    #     self.max_calls = current_secret["remaining_requests"]
    #     print("Changing Serper search SECRET")

    def _get_serper_search_results(self, search_string, location_ISO_code, page):
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        payload = json.dumps({
            "q": search_string,
            "gl": location_ISO_code.lower(),
            "page": page
        })
        # print(payload, self.api_key)

        try:
            response = requests.post(self.serper_url, headers=headers, data=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return {"organic": []}
        
    def update_final_state(self):
        """Update the secrets file one final time to persist the final state"""
        self._update_secrets_file()
    

    def fetch_results(self, search_string, pages_before_date, location_ISO_code, n_pages):
        search_results = {}
        search_string = f"{search_string}"
        # search_string = f"{search_string} before:{pages_before_date}"
        
        for page_num in range(n_pages):
            if self.max_calls <= 0 or not self.api_key:
                self._update_secrets_file()  # Update before rotating
                self._rotate_secret()
            
            page_results = self._get_serper_search_results(search_string, location_ISO_code, page_num+1)
            search_results[page_num+1] = page_results["organic"]
            self.max_calls -= 1
            self.request_counter += 1
            
            # Update secrets file every 10 requests
            if self.request_counter % 10 == 0:
                self._update_secrets_file()
        return search_results
