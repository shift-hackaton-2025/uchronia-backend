from pydantic import BaseModel
from typing import List, Optional

class Option(BaseModel):
    title: str
    option_img_link: Optional[str] = None
    consequence: str
    consequence_img_link: Optional[str] = None

class Event(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    date: str
    options: List[Option]
