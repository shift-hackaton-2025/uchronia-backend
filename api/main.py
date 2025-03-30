from fastapi import FastAPI, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from typing import List, Optional
import json
import os
from pydantic import BaseModel
import uuid
from services.create_rag.choose_image import find_closest_event_id
from services.generate_events import (
    generate_future_events,
    generate_narrative_arc_events,
)
from services.generate_final_report import generate_final_report
from services.create_rag.generate_image import generate_image
from models.event import Event
from services.music.choose_music import choose_music

app = FastAPI()

# Create images directory if it doesn't exist
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "generated_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

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

# In-memory task status tracker
image_task_status = {}

class UpdateEventsRequest(BaseModel):
    events: List[Event]
    option_chosen: str
    model: str = "gpt-4o"
    temperature: float = 0.7

class UpdateEventsResponse(BaseModel):
    events: List[Event]
    image_tasks: List[dict]

class Summary(BaseModel):
    description: str
    # achievement: str
    # chaos_level: str

class ImageGenerationResponse(BaseModel):
    task_id: str
    status: str

class ImageStatus(BaseModel):
    status: str
    image_url: Optional[str] = None

@app.get("/", status_code=200)
async def healthcheck():
    return {"status": "healthy"}

@app.get("/version", status_code=200)
async def get_version():
    """Return a hardcoded version to confirm deployment"""
    return {"version": "1.0.0", "name": "uchronia-backend", "timestamp": "2025-03-30"}

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
            "description": story["description"],
            "image": story["img"],  # No image links in the source data
            "date": story["date"],  # No dates in the source data
            "music_file": story["music_file"],
            "options": []
        }

        # For each option in the story, create an option with its consequence
        for option in story["options"]:
            event["options"].append({
                "title": option["title"],
                "img": option["img"],
                "consequence": option["consequence"],
                "music_file": option["music_file"]
            })

        events.append(event)

    return events[:4]  # Return only the first 4 events to match the expected response


@app.post("/update_events", response_model=UpdateEventsResponse)
async def update_events(request: UpdateEventsRequest, background_tasks: BackgroundTasks):
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

    # filter events to remove future events and remove options for past events
    print("Original events:", [{"id": e.id, "date": e.date, "title": e.title} for e in request.events])

    # Sort events by date first
    sorted_events = sorted(request.events, key=lambda x: x.date)
    print("Sorted events:", [{"id": e.id, "date": e.date, "title": e.title} for e in sorted_events])

    chosen_event_index = next(i for i, e in enumerate(sorted_events) if e.id == event_id)
    print(f"Chosen event index: {chosen_event_index}")

    # Keep all events up to and including the chosen event
    filtered_events = sorted_events[:chosen_event_index + 1]
    print("Filtered events:", [{"id": e.id, "date": e.date, "title": e.title} for e in filtered_events])

    # Generate new events
    # _, new_events = generate_future_events(filtered_events, chosen_option, request.model, request.temperature)
    new_events = await generate_narrative_arc_events(filtered_events, chosen_option)

    # Start image generation tasks for new events
    image_tasks = []
    for event in new_events:
        # Main event image
        task_id = str(uuid.uuid4())
        background_tasks.add_task(generate_image_task, event["title"], task_id)
        image_tasks.append({
            "event_id": event["id"],
            "task_id": task_id,
            "type": "event"
        })
        image_id = find_closest_event_id(event["title"] + " - Year : " + event["date"])
        event["img"] = f"https://uchronia.s3.eu-west-3.amazonaws.com/image_{image_id}.png"

        # Options images
        for idx, option in enumerate(event["options"]):
            # Option image
            option_task_id = str(uuid.uuid4())
            background_tasks.add_task(generate_image_task, option["title"], option_task_id)
            image_tasks.append({
                "event_id": event["id"],
                "option_id": idx,
                "task_id": option_task_id,
                "type": "option"
            })
            image_id = find_closest_event_id(option["title"] + "- Year :" + event["date"])
            option["img"] = f"https://uchronia.s3.eu-west-3.amazonaws.com/image_{image_id}.png"

        # Choose music for the event
        event["music_file"] = choose_music(event["title"] + " " + event["description"])
        # Choose music for options
        for option in event["options"]:
            option["music_file"] = choose_music(option["title"] + " " + event["title"])

    return UpdateEventsResponse(events=new_events, image_tasks=image_tasks)

@app.post("/exit_game", response_model=Summary)
async def exit_game(request: List[Event]):
    # Use the provided list of events
    events = request
    print("events", events)
    if not events:
        raise HTTPException(status_code=404, detail=f"Events not found")
    
    # Set default values for model and temperature as they are not provided in the input JSON
    model = "gpt-4o"
    temperature = 0.7
    summary = await generate_final_report(events, model, temperature)
    
    if summary:
        return summary
    else:
        raise HTTPException(status_code=500, detail="Error generating final report")

async def generate_image_task(prompt: str, task_id: str):
    output_path = os.path.join(IMAGES_DIR, f"{task_id}.png")
    try:
        # Set task as processing in our in-memory tracker
        image_task_status[task_id] = "processing"
        generate_image(prompt, output_path)
        # Update status when completed
        image_task_status[task_id] = "completed"
    except Exception as e:
        # Log the error and update status
        print(f"Error generating image for task {task_id}: {str(e)}")
        image_task_status[task_id] = "error"

@app.post("/generate-image")
async def request_image_generation(prompt: str, background_tasks: BackgroundTasks) -> ImageGenerationResponse:
    task_id = str(uuid.uuid4())
    # Initialize task status
    image_task_status[task_id] = "processing"
    background_tasks.add_task(generate_image_task, prompt, task_id)
    return ImageGenerationResponse(task_id=task_id, status="processing")

@app.get("/image-status/{task_id}")
async def get_image_status(task_id: str, response: Response) -> ImageStatus:
    """
    Check the status of an image generation task without waiting for completion.
    Returns immediately with the current status.
    Optimized for parallel requests.
    """
    # Set cache control headers to prevent browser caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    # Check in-memory status first to avoid file system operations when possible
    status = image_task_status.get(task_id, "unknown")
    
    if status == "completed":
        # Only check file system if our in-memory status says it's completed
        image_path = os.path.join(IMAGES_DIR, f"{task_id}.png")
        if os.path.exists(image_path):
            return ImageStatus(
                status="completed",
                image_url=f"data/generated_images/{task_id}.png"
            )
        
    # For processing, error, or unknown status
    return ImageStatus(status=status)
