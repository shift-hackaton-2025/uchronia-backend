from fastapi import FastAPI, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
import logging
import time
from typing import List, Optional
import json
import os
from pydantic import BaseModel
import uuid
from services.create_rag.choose_image import find_closest_event_id, find_closest_event_ids, find_closest_event_ids_async
from services.generate_events import (
    generate_future_events,
    generate_narrative_arc_events,
)
from services.generate_final_report import generate_final_report
from services.create_rag.generate_image import generate_image
from models.event import Event
from services.music.choose_music import choose_music, choose_music_batch, choose_music_batch_async
import asyncio

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Initialize status tracker with existing images
def initialize_image_status():
    for filename in os.listdir(IMAGES_DIR):
        if filename.endswith('.png'):
            # Extract task_id from filename (remove .png extension)
            task_id = filename.replace('.png', '')
            # Mark the task as completed
            image_task_status[task_id] = "completed"
    print(f"Initialized image status tracker with {len(image_task_status)} completed images")

# Run the initialization
initialize_image_status()

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

class ImageBatchStatusRequest(BaseModel):
    task_ids: List[str]

class ImageBatchStatusResponse(BaseModel):
    statuses: dict

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
    start_time = time.time()
    logger.info(f"=== Starting update_events with chosen option: {request.option_chosen} ===")
    
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
    logger.info(f"Processing chosen option: {chosen_option['title']}")

    # filter events to remove future events and remove options for past events
    logger.info(f"Original events count: {len(request.events)}")

    # Sort events by date first
    sorted_events = sorted(request.events, key=lambda x: x.date)
    chosen_event_index = next(i for i, e in enumerate(sorted_events) if e.id == event_id)
    logger.info(f"Chosen event index: {chosen_event_index}")

    # Keep all events up to and including the chosen event
    filtered_events = sorted_events[:chosen_event_index + 1]
    logger.info(f"Filtered events count: {len(filtered_events)}")

    # Generate new events
    logger.info("Starting narrative arc events generation...")
    generation_start = time.time()
    new_events = await generate_narrative_arc_events(filtered_events, chosen_option)
    logger.info(f"Events generation completed in {time.time() - generation_start:.2f} seconds")
    logger.info(f"Generated {len(new_events)} new events")

    # START OPTIMIZATION: Batch image and music processing
    # Prepare all prompts for image finding at once
    logger.info("Preparing batch processing for images and music...")
    batch_start = time.time()
    
    event_image_prompts = []
    event_indices = []
    option_image_prompts = []
    option_indices = []
    music_prompts = []
    music_indices = []
    
    # Collect all prompts first
    for event_idx, event in enumerate(new_events):
        # Event image prompt
        event_image_prompts.append(event["title"] + " - Year : " + event["date"])
        event_indices.append((event_idx, None))
        
        # Event music prompt
        music_prompts.append(event["title"] + " " + event["description"])
        music_indices.append((event_idx, None))
        
        # Option prompts
        for option_idx, option in enumerate(event["options"]):
            # Option image prompt
            option_image_prompts.append(option["title"] + "- Year :" + event["date"])
            option_indices.append((event_idx, option_idx))
            
            # Option music prompt
            music_prompts.append(option["title"] + " " + event["title"])
            music_indices.append((event_idx, option_idx))
    
    # Process all image IDs and music selections concurrently using async functions
    logger.info(f"Finding image IDs and music for all events and options...")
    
    # Run the async operations concurrently to save time
    event_image_ids, option_image_ids, all_music_files = await asyncio.gather(
        find_closest_event_ids_async(event_image_prompts),
        find_closest_event_ids_async(option_image_prompts),
        choose_music_batch_async(music_prompts)
    )
    
    # Now assign all the results back to the events and options
    logger.info("Assigning image IDs and music files...")
    
    # Assign event images and music
    for i, (event_idx, _) in enumerate(event_indices):
        event = new_events[event_idx]
        image_id = event_image_ids[i]
        event["image"] = f"https://uchronia.s3.eu-west-3.amazonaws.com/image_{image_id}.png"
        event["music_file"] = all_music_files[music_indices.index((event_idx, None))]
    
    # Assign option images and music
    for i, (event_idx, option_idx) in enumerate(option_indices):
        option = new_events[event_idx]["options"][option_idx]
        image_id = option_image_ids[i]
        option["img"] = f"https://uchronia.s3.eu-west-3.amazonaws.com/image_{image_id}.png"
        option["music_file"] = all_music_files[music_indices.index((event_idx, option_idx))]
    
    logger.info(f"Batch processing completed in {time.time() - batch_start:.2f} seconds")
    # END OPTIMIZATION
    
    # Start image generation tasks for new events
    logger.info("Starting background image generation tasks...")
    image_tasks = []
    task_start = time.time()
    
    for event_idx, event in enumerate(new_events):
        # Main event image
        task_id = str(uuid.uuid4())
        logger.info(f"Adding background task for event image: {event['title'][:30]}...")
        background_tasks.add_task(generate_image_task, event["title"], task_id)
        image_tasks.append({
            "event_id": event["id"],
            "task_id": task_id,
            "type": "event"
        })
        
        # Options images
        for idx, option in enumerate(event["options"]):
            # Option image
            option_task_id = str(uuid.uuid4())
            logger.info(f"Adding background task for option image: {option['title'][:30]}...")
            background_tasks.add_task(generate_image_task, option["title"], option_task_id)
            image_tasks.append({
                "event_id": event["id"],
                "option_id": idx,
                "task_id": option_task_id,
                "type": "option"
            })
    
    logger.info(f"All background tasks added in {time.time() - task_start:.2f} seconds")
    logger.info(f"Added {len(image_tasks)} image generation tasks")
    logger.info(f"=== update_events completed in {time.time() - start_time:.2f} seconds ===")

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
        await run_in_threadpool(generate_image, prompt, output_path)
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
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    status = image_task_status.get(task_id)
    if status is None:
        return ImageStatus(status="processing")

    if status == "completed":
        image_path = os.path.join(IMAGES_DIR, f"{task_id}.png")
        exists = await run_in_threadpool(os.path.exists, image_path)
        if exists:
            return ImageStatus(
                status="completed", image_url=f"data/generated_images/{task_id}.png"
            )

    return ImageStatus(status=status)


@app.post("/batch-image-status")
async def batch_get_image_status(request: ImageBatchStatusRequest) -> ImageBatchStatusResponse:
    """
    Check the status of multiple image generation tasks in a single request.
    Returns immediately with the current status of all requested tasks.
    """
    results = {}
    
    # Process each task ID
    for task_id in request.task_ids:
        # Check in-memory status first (super fast)
        status = image_task_status.get(task_id)
        
        # If task_id not in dictionary, mark as processing without file check
        if status is None:
            results[task_id] = {"status": "processing"}
            continue
            
        # Only check file system if our in-memory status says it's completed
        if status == "completed":
            image_path = os.path.join(IMAGES_DIR, f"{task_id}.png")
            if os.path.exists(image_path):
                results[task_id] = {
                    "status": "completed", 
                    "image_url": f"data/generated_images/{task_id}.png"
                }
                continue
                
        # For any other status
        results[task_id] = {"status": status}
    
    return ImageBatchStatusResponse(statuses=results)
