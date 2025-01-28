import google.generativeai as genai
from google.generativeai import GenerationConfig
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from itertools import cycle
import json
import time
from time import perf_counter
from typing import List

class GeminiAPI:
    def __init__(
        self,
        secrets_file,
        model_name="gemini-1.5-flash-latest",
        response_schema=None,
        temperature=0.75,
        top_p=0.9,
        response_mime_type="text/plain",
        safety_settings=None,
    ):
        """
        Initializes the GeminiAPI with the specified configurations.

        Args:
            model_name (str): Name of the Gemini model to use.
            secrets_file (str): Path to the JSON file containing API keys.
            response_schema (dict, optional): JSON schema for the expected response.
                                              Defaults to None.
            temperature (float, optional): Sampling temperature. Defaults to 0.25.
            top_p (float, optional): Top-p sampling parameter. Defaults to 0.9.
            top_k (int, optional): Top-k sampling parameter. Defaults to 40.
            response_mime_type (str, optional): MIME type of the response. Defaults to "text/plain".
            safety_settings (dict, optional): Safety settings for content generation.
                                              If None, default settings are applied.
        """
        self.model_name = model_name
        self.generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
        )
        
        # Default safety settings
        if safety_settings is None:
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                # HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY: HarmBlockThreshold.BLOCK_NONE
            }
        else:
            self.safety_settings = safety_settings

        # Configure API keys and rate limiting (Free version)
        if "flash" in model_name:
            if "1.5" in model_name:
                self.max_requests_per_key = 1500 # requests per day
                self.rpm = 15 # requests per minute
            elif "2.0" in model_name:
                self.max_requests_per_key = 1500
                self.rpm = 10
            else:
                print("Unknown Gemini model name")
                return
        elif "pro" in model_name:
            self.max_requests_per_key = 50
            self.rpm = 2
        else:
            print("Unknown Gemini model name")
            return

        self.sleep_time = 60 / self.rpm
        self.embed_sleep_time = 0.04

        self.request_count = 0

        with open(secrets_file, "r") as f:
            self.api_keys = cycle(json.load(f)["keys"])

        self.get_model = self.get_gemini_model()
        self.model = self.get_model()

    def get_gemini_model(self):
        """
        Initializes and returns a function to get the current Gemini model using the next API key.
        """
        def initialize_model():
            current_key = next(self.api_keys)
            print("Using key: ****" + current_key[-5:])
            genai.configure(api_key=current_key)
            return genai.GenerativeModel(
                self.model_name,
                safety_settings=self.safety_settings
            )
        return initialize_model

    def get_llm_response(self, input_text):
        """
        Generates a response from the Gemini model based on the input_text using generate_content.
        Args:
            input_text (str): The prompt to send to the model.
        Returns:
            str or None: The model's response in the specified MIME type if successful, else None.
        """
        if self.request_count >= self.max_requests_per_key:
            self.model = self.get_model()
            self.request_count = 0

        try:
            start_time = perf_counter()
            response = self.model.generate_content(
                input_text,
                generation_config=self.generation_config
            )
            elapsed_time = perf_counter() - start_time
            # Only sleep if the API call took less time than the required sleep time
            if self.sleep_time > elapsed_time:
                time.sleep(self.sleep_time - elapsed_time)

            self.request_count += 1

            return response
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(self.sleep_time)
            return None
        
    def get_chat_response(self, input_text, chat=None, reset=True):
        if self.request_count >= self.max_requests_per_key:
            self.model = self.get_model()
            self.request_count = 0

        if reset:
            chat = self.model.start_chat(history=[])
        try:
            start_time = perf_counter()
            response = chat.send_message(content=input_text, 
                                     generation_config=self.generation_config)
            elapsed_time = perf_counter() - start_time
            # Only sleep if the API call took less time than the required sleep time
            if self.sleep_time > elapsed_time:
                time.sleep(self.sleep_time - elapsed_time)

            self.request_count += 1
            return response
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(self.sleep_time)
            return None
        
    def get_text_embeddings(self, batched_text: List[str], out_dim=None, task="semantic_similarity"):
        if out_dim:
            result = genai.embed_content(model="models/text-embedding-004", 
                                content=batched_text,
                                output_dimensionality=out_dim,
                                task_type=task
                                )
        else:
            result = genai.embed_content(model="models/text-embedding-004", 
                                content=batched_text,
                                task_type=task
                                )
        time.sleep(self.embed_sleep_time)
        return result['embedding']

# Usage Example:

# if __name__ == "__main__":
#     import json

#     # Define the response schema for triples
#     response_schema = {
#         "type": "array",
#         "items": {
#             "type": "object",
#             "properties": {
#                 "subject": {
#                     "type": "string",
#                 },
#                 "predicate": {
#                     "type": "string",
#                 },
#                 "object": {
#                     "type": "string",
#                 },
#             },
#             "required": ["subject", "predicate", "object"],
#         },
#     }

#     # Initialize the GeminiAPI with the desired configurations
#     gemini_api = GeminiAPI(
#         model_name="gemini-1.5-flash-latest",
#         secrets_file="path/to/secrets.json",  # Replace with your actual secrets file path
#         response_schema=response_schema,
#         temperature=0.35,
#         top_p=0.9,
#         top_k=40,
#         response_mime_type="application/json"
#     )

#     # Define the prompt for generating triples
#     final_prompt = (
#         "List a few triples suitable for a knowledge graph. Each triple should include a Subject, "
#         "Predicate, and Object. Provide the output in JSON format as an array of objects with "
#         "keys 'subject', 'predicate', and 'object'."
#     )

#     # Generate the response
#     response = gemini_api.get_llm_response(final_prompt)

#     # Process and print the response
#     if response:
#         try:
#             triples = response.text  # Assuming response.text contains the JSON string
#             print("Raw Response:")
#             print(triples)
#             # Optionally, parse the JSON
#             triples_json = json.loads(triples)
#             print("\nParsed JSON:")
#             print(json.dumps(triples_json, indent=4))
#         except json.JSONDecodeError as e:
#             print("Failed to parse JSON response:", e)
#     else:
#         print("No response received.")
