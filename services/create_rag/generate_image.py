import requests
import time
import sys
import os

from dotenv import load_dotenv

load_dotenv()

# Load all API keys
SEELAB_API_KEYS = [
    os.getenv("SEELAB_API_KEY_1"),
    # os.getenv("SEELAB_API_KEY_2"),
    # os.getenv("SEELAB_API_KEY_3"),
    # os.getenv("SEELAB_API_KEY_4"),
]
assert all(key is not None for key in SEELAB_API_KEYS), "One or more API keys are None"

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
    for api_key in SEELAB_API_KEYS:
        try:
            session_id = initiate_image_generation(api_key, prompt)
            image_url = poll_image_status(api_key, session_id)

            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Created directory: {output_dir}")

            response = requests.get(image_url)
            response.raise_for_status()
            with open(output_path, "wb") as file:
                file.write(response.content)
            return  # Return after successful image generation
        except requests.HTTPError as http_err:
            print(f"HTTP error occurred with API key {api_key}: {http_err}")
        except RuntimeError as runtime_err:
            print(f"Runtime error with API key {api_key}: {runtime_err}")
        except Exception as err:
            print(f"An unexpected error occurred with API key {api_key}: {err}")
    sys.exit(1)  # Exit if all API keys fail


async def generate_image_async(prompt: str, output_path: str):
    for api_key in SEELAB_API_KEYS:
        try:
            session_id = await initiate_image_generation_async(api_key, prompt)
            image_url = await poll_image_status_async(api_key, session_id)

            output_dir = os.path.dirname(output_path)
            # Offload directory creation if necessary
            if output_dir and not await run_in_threadpool(os.path.exists, output_dir):
                await run_in_threadpool(os.makedirs, output_dir)
                print(f"Created directory: {output_dir}")

            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                async with aiofiles.open(output_path, "wb") as file:
                    await file.write(response.content)
            return
        except httpx.HTTPError as http_err:
            print(f"HTTP error occurred with API key {api_key}: {http_err}")
        except RuntimeError as runtime_err:
            print(f"Runtime error with API key {api_key}: {runtime_err}")
        except Exception as err:
            print(f"An unexpected error occurred with API key {api_key}: {err}")
    # Optionally, raise an error if all API keys fail
    raise Exception("All API keys failed")


if __name__ == "__main__":
    
    prompt = "Generate image of a futuristic city skyline at sunset"
    output_path = "output/futuristic_city_skyline.png"

    generate_image(prompt, output_path)
