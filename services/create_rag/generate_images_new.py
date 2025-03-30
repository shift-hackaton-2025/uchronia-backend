import yaml
import os

from generate_image import generate_image

OUTPUT_DIRECTORY = "services/create_rag/rag"

with open("services/create_rag/events.yaml", "r") as file:
    events = yaml.safe_load(file)


for i, event in enumerate(events, start=1):
    event_id = event['id']
    if event_id >= 0:
        prompt = f"{event['name']}: {event['description']}"
        output_file = f"image_{event_id}.png"
        output_path = os.path.join(OUTPUT_DIRECTORY, output_file)
        generate_image(prompt, output_path)
        print(f"Generated image for event {event_id}")
