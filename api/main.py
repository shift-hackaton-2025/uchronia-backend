from fastapi import FastAPI, HTTPException
from typing import List, Optional
import json
import os
from pydantic import BaseModel
from services.generate_events import generate_future_events

app = FastAPI()

class Option(BaseModel):
    title: str
    option_img_link: Optional[str] = None
    consequence: str
    consequence_img_link: Optional[str] = None


class Event(BaseModel):
    id: str
    title: str
    image: Optional[str] = None
    date: str
    options: List[Option]


class UpdateEventsRequest(BaseModel):
    events: List[Event]
    option_chosen: str
    model: str = "gpt-4o"
    temperature: float = 0.7


@app.get("/", status_code=200)
async def healthcheck():
    return {"status": "healthy"}

@app.get("/get_initial_events", response_model=List[Event])
async def get_initial_events():
    """Return events from the starting deck JSON file with options and consequences"""
    # Get the path to the JSON file
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "starting_deck.json")
    
    # Read the JSON file
    with open(json_path, "r") as f:
        data = json.load(f)
    

    # Convert the data to match our API model
    events = []
    for story in data["stories"]:
        # For each story, create an event
        event = {
            "id": story["id"],
            "title": story["title"],
            "image": "",  # No image links in the source data
            "date": "",  # No dates in the source data
            "options": []
        }

        # For each option in the story, create an option with its consequence
        for option in story["options"]:
            event["options"].append({
                "title": option["title"],
                "option_img_link": "",
                "consequence": option["consequence"],
                "consequence_img_link": ""
            })

        events.append(event)

    return events[:4]  # Return only the first 4 events to match the expected response


@app.post("/update_events", response_model=List[Event])
def update_events(request: UpdateEventsRequest):
    # option_chosen format: "{event_id}_{option_idx}"
    event_id, option_idx = map(str, request.option_chosen.split("_"))
    
    # Find the event that was chosen
    event = next((event for event in request.events if event.id == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event with id {event_id} not found")
    
    chosen_option = {
        "title": event.options[int(option_idx)].title,
        "consequence": event.options[int(option_idx)].consequence
    }
    
    _, raw_events = generate_future_events(request.events, chosen_option, request.model, request.temperature)
    
    # Transform raw events into Event model format
    new_events = []
    for raw_event in raw_events:
        event = {
            "id": raw_event["id"],
            "title": raw_event["title"],
            "image": "",
            "date": "",  # We might want to generate this in the future
            "options": [
                {
                    "title": opt["title"],
                    "option_img_link": "",
                    "consequence": opt["consequence"],
                    "consequence_img_link": ""
                } for opt in raw_event["options"]
            ]
        }
        new_events.append(event)
    
    return new_events