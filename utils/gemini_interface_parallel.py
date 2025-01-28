import google.generativeai as genai
from google.generativeai import GenerationConfig
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from itertools import cycle
import json
import time
from time import perf_counter
from typing import List
import multiprocessing

class GeminiAPI:
    def __init__(
        self,
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
            response_schema (dict, optional): JSON schema for the expected response.
                                              Defaults to None.
            temperature (float, optional): Sampling temperature. Defaults to 0.25.
            top_p (float, optional): Top-p sampling parameter. Defaults to 0.9.
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
            }
        else:
            self.safety_settings = safety_settings

        # Configure API keys and rate limiting (Free version)
        if "flash" in model_name:
            self.max_requests_per_key = 1475 # requests per day
            if "1.5" in model_name:
                self.rpm = 15 # requests per minute
            elif "2.0" in model_name:
                self.rpm = 10
            else:
                print("Unknown Gemini model name")
                return
        elif "pro" in model_name:
            self.max_requests_per_key = 45
            self.rpm = 2
        else:
            print("Unknown Gemini model name")
            return

        self.sleep_time = 60 / self.rpm
        self.embed_sleep_time = 0.04

        print("Configured process time: ", self.sleep_time)

        self.request_count = 0

    def initialize_model(self, api_key):
        """
        Initializes the Gemini model with the given API key.
        """
        print(f"Process {multiprocessing.current_process().name} using key: ****{api_key[-5:]}")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            self.model_name,
            safety_settings=self.safety_settings
        )

    def get_llm_response(self, input_text):
        """
        Generates a response from the Gemini model based on the input_text using generate_content.
        Args:
            input_text (str): The prompt to send to the model.
        Returns:
            str or None: The model's response in the specified MIME type if successful, else None.
        """
        if self.request_count >= self.max_requests_per_key:
            print(f"Key exhausted in process {multiprocessing.current_process().name}. You need to manually change the key.")
            return None

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
            print(f"Key exhausted in process {multiprocessing.current_process().name}. You need to manually change the key.")
            return None

        if reset:
            chat = self.model.start_chat(history=[])
        try:
            start_time = perf_counter()
            response = chat.send_message(content=input_text,
                                         generation_config=self.generation_config)
            elapsed_time = perf_counter() - start_time
            # Only sleep if the API call took less time than the required sleep time
            if elapsed_time < self.sleep_time:
                time.sleep(self.sleep_time - elapsed_time)
                
            # Extra sleep to avoid rate limiting
            time.sleep(2.0)

            self.request_count += 1
            return response
        except Exception as e:
            if "429 Resource has been exhausted" in str(e):
                print("Error: 429 Resource has been exhausted. Backing off...")
                time.sleep(60)
            else:
                print(f"Error: {e}")
                time.sleep(self.sleep_time)
            return None

    def get_text_embeddings(self, batched_text: List[str], out_dim=768, task="semantic_similarity"):
        result = genai.embed_content(model="models/text-embedding-004",
                            content=batched_text,
                            output_dimensionality=out_dim,
                            task_type=task
                            )
        time.sleep(self.embed_sleep_time)
        return result['embedding']

def worker_process(api_key, input_queue, output_queue, model_name, temperature, top_p):
    import random

    """
    Worker function for each process.
    """
    gemini_api = GeminiAPI(
        model_name=model_name,
        temperature=temperature,
        top_p=top_p,
    )
    gemini_api.initialize_model(api_key)

    while True:
        try:
            task = input_queue.get()
            task_type = task[0]
            task_id = task[2]
            print(f"Process {multiprocessing.current_process().name} - received task-id: {task_id}")

            if task_type == "sentinel":  # Sentinel value indicates termination
                input_queue.task_done()
                break
            elif task_type == "chat":
                input_text = task[1] 
                response = gemini_api.get_chat_response(input_text)
            elif task_type == "embed":
                batched_text = task[1]
                out_dim = task[2]
                task_type = task[3]
                response = gemini_api.get_text_embeddings(batched_text, out_dim, task_type)
            else:
                raise ValueError("Invalid task type")

            # response = "This is a test response"
            # Sleep for a random amount of time between 0 and 1 seconds
            # time.sleep(random.uniform(0, 3))
            
            output_queue.put((response, task_id))
            input_queue.task_done()
        except Exception as e:
            print(f"Error in worker process: {e}")
            output_queue.put((None, task_id))  # Indicate failure
            input_queue.task_done()
    print(f"Process {multiprocessing.current_process().name} - EXITING..")

def batch_process(prompts, secrets_file, model_name, temperature, top_p):
    # Read API keys
    with open(secrets_file, "r") as f:
        api_keys = json.load(f)["keys"]

    # Create input and output queues
    input_queue = multiprocessing.JoinableQueue()
    output_queue = multiprocessing.Queue()

    # Create and start worker processes
    processes = []
    for api_key in api_keys[:len(prompts)]:
        process = multiprocessing.Process(
            target=worker_process,
            args=(api_key, input_queue, output_queue, model_name, temperature, top_p)
        )
        processes.append(process)
        process.start()

    print(f"Total processes: {len(processes)}")
    print(f"Total prompts: {len(prompts)}")
    for prompt in prompts:
        input_queue.put(prompt)

    # Add sentinel values to signal processes to terminate
    for i in range(len(processes)):
        input_queue.put(("sentinel", "", -1))

    # Create a list to store results
    results = []
    
    # Track completed tasks and total expected tasks
    completed_tasks = 0
    total_tasks = len(prompts)
    
    # Collect results as they come in
    while completed_tasks < total_tasks:
        result = output_queue.get()
        results.append(result)
        completed_tasks += 1
    
    print(f"All tasks completed")

    # Clean up processes
    for process in processes:
        process.join(timeout=10)  # Wait up to 10 seconds
        if process.is_alive():
            print(f"Process {process.name} did not terminate in time, forcing termination")
            process.terminate()  # Force termination if still running
            process.join()  # Wait for termination to complete
        process.close()
    print(f"All processes terminated")

    return results
