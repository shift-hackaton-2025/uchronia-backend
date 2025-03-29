import requests
import time
import sys
import os

from dotenv import load_dotenv

load_dotenv()

SEELAB_API_KEY = os.getenv("SEELAB_API_KEY")
assert SEELAB_API_KEY is not None, "key is None"
API_URL = "https://app.seelab.ai/api/predict"
POLLING_INTERVAL = 3


def initiate_image_generation(api_key, prompt):
    response = requests.post(
        url=f"{API_URL}/text-to-image",
        json={"params": {'prompt': prompt}},
        headers={"Authorization": f"Token {api_key}"}
    )
    response.raise_for_status()
    session = response.json()
    return session['id']

  
def poll_image_status(api_key, session_id):
    while True:
        response = requests.get(
            url=f"{API_URL}/session/{session_id}",
            headers={"Authorization": f"Token {api_key}"}
        )
        response.raise_for_status()
        result = response.json()
        status = result['state']

        if status == 'succeed':
            return result['result']['image'][0]['links']['original']
        elif status == 'failed':
            raise RuntimeError(f"Image generation failed: {result['job'].get('error', 'Unknown error')}")
        else:
            # print(f'Waiting for the result of session {session_id}...')
            time.sleep(POLLING_INTERVAL)


def generate_image(prompt, output_path):
    try:
        session_id = initiate_image_generation(SEELAB_API_KEY, prompt)
        image_url = poll_image_status(SEELAB_API_KEY, session_id)
        
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        response = requests.get(image_url)
        response.raise_for_status()
        with open(output_path, "wb") as file:
            file.write(response.content)

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        sys.exit(1)
    except RuntimeError as runtime_err:
        print(f"Runtime error: {runtime_err}")
        sys.exit(1)
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
        sys.exit(1)


if __name__ == "__main__":
    
    prompt = "Generate image of a futuristic city skyline at sunset"
    output_path = "output/futuristic_city_skyline.png"

    generate_image(prompt, output_path)
