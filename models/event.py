from pydantic import BaseModel
from typing import List, Optional

class Option(BaseModel):
    title: str
    consequence: List[str]
    img: Optional[str] = None
    music_file: Optional[str] = None

class Event(BaseModel):
    id: str
    title: str
    description: Optional[List[str]] = None
    image: Optional[str] = None
    date: str
    music_file: Optional[str] = None
    options: List[Option]
