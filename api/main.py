from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from typing import List, Optional
import json
import os
from pydantic import BaseModel
from services.generate_events import generate_future_events 
from services.generate_final_report import generate_final_report

app = FastAPI()

# Mount the static files directory
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
app.mount("/data", StaticFiles(directory=static_dir), name="data")

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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

class Summary(BaseModel):
    description: str
    # achievement: str
    # chaos_level: str

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
            "image": story["img"],  # No image links in the source data
            "date": story["date"],  # No dates in the source data
            "options": []
        }

        # For each option in the story, create an option with its consequence
        for option in story["options"]:
            event["options"].append({
                "title": option["title"],
                "option_img_link": option["img"],
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

    # filter events to remove, future events and remove options for past events
    print("Original events:", [{"id": e.id, "date": e.date, "title": e.title} for e in request.events])
    
    # Sort events by date first
    sorted_events = sorted(request.events, key=lambda x: x.date)
    print("Sorted events:", [{"id": e.id, "date": e.date, "title": e.title} for e in sorted_events])
    
    chosen_event_index = next(i for i, e in enumerate(sorted_events) if e.id == event_id)
    print(f"Chosen event index: {chosen_event_index}")
    
    # Keep all events up to and including the chosen event
    filtered_events = sorted_events[:chosen_event_index + 1]
    print("Filtered events:", [{"id": e.id, "date": e.date, "title": e.title} for e in filtered_events])
    
    _, raw_events = generate_future_events(filtered_events, chosen_option, request.model, request.temperature)
    
    # Transform raw events into Event model format
    new_events = []
    for raw_event in raw_events:
        event = {
            "id": raw_event["id"],
            "title": raw_event["title"],
            "image": None,
            "date": raw_event["date"],
            "options": [
            {
                "title": opt["title"],
                "option_img_link": None,
                "consequence": opt["consequence"],
                "consequence_img_link": None
            }
            for idx, opt in enumerate(raw_event["options"], start=1)
            ]
        }
        new_events.append(event)
    
    return new_events

@app.post("/exit_game", response_model=Summary)
def exit_game(request: List[Event]):
    # Use the provided list of events
    events = request
    print("events", events)
    if not events:
        raise HTTPException(status_code=404, detail=f"Events not found")
    
    # Set default values for model and temperature as they are not provided in the input JSON
    model = "gpt-4o"
    temperature = 0.7
    summary = generate_final_report(events, model, temperature)
    
    if summary:
        return summary
    else:
        raise HTTPException(status_code=500, detail="Error generating final report")