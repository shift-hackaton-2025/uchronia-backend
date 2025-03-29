from fastapi import FastAPI
from datetime import date
from typing import List
import json
import os
from pydantic import BaseModel

app = FastAPI()

class Option(BaseModel):
    text: str
    option_img_link: str

class Consequence(BaseModel):
    text: str
    consequence_img_link: str

class Event(BaseModel):
    title: str
    event_image_link: str
    date: str
    options: List[Option]
    consequences: List[Consequence]

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
            "title": story["title"],
            "event_image_link": "",  # No image links in the source data
            "date": "",  # No dates in the source data
            "options": [],
            "consequences": []
        }
        
        # For each option in the story, create an option and a consequence
        for option in story["options"]:
            event["options"].append({
                "text": option["title"],
                "option_img_link": ""
            })
            
            event["consequences"].append({
                "text": option["consequence"],
                "consequence_img_link": ""
            })
        
        events.append(event)
    
    return events[:4]  # Return only the first 4 events to match the expected response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)