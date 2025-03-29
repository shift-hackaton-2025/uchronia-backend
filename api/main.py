from fastapi import FastAPI
from datetime import date
from typing import List
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

@app.get("/get_initial_events", response_model=List[Event])
async def get_initial_events():
    """Return 4 sample events with options and consequences including image links"""
    return [
        {
            "title": "Economic Crisis",
            "event_image_link": "",
            "date": "2026-03-29",
            "options": [
                {
                    "text": "Increase taxes to fund social programs",
                    "option_img_link": ""
                },
                {
                    "text": "Cut government spending to reduce debt",
                    "option_img_link": ""
                }
            ],
            "consequences": [
                {
                    "text": "Public satisfaction improves but business growth slows",
                    "consequence_img_link": ""
                },
                {
                    "text": "Short-term economic relief but public services suffer",
                    "consequence_img_link": ""
                }
            ]
        },
        {
            "title": "Environmental Disaster",
            "event_image_link": "",
            "date": "2026-04-15",
            "options": [
                {
                    "text": "Implement strict environmental regulations",
                    "option_img_link": ""
                },
                {
                    "text": "Offer subsidies for green technology adoption",
                    "option_img_link": ""
                }
            ],
            "consequences": [
                {
                    "text": "Immediate positive impact but business opposition grows",
                    "consequence_img_link": ""
                },
                {
                    "text": "Gradual improvement with better industry acceptance",
                    "consequence_img_link": ""
                }
            ]
        },
        {
            "title": "Healthcare System Overload",
            "event_image_link": "",
            "date": "2026-05-10",
            "options": [
                {
                    "text": "Invest heavily in hospital infrastructure",
                    "option_img_link": ""
                },
                {
                    "text": "Launch preventive care public awareness campaign",
                    "option_img_link": ""
                }
            ],
            "consequences": [
                {
                    "text": "Long construction times but permanent capacity increase",
                    "consequence_img_link": ""
                },
                {
                    "text": "Slower results but more sustainable long-term benefits",
                    "consequence_img_link": ""
                }
            ]
        },
        {
            "title": "Education Reform",
            "event_image_link": "",
            "date": "2026-06-20",
            "options": [
                {
                    "text": "Redesign curriculum to focus on STEM fields",
                    "option_img_link": ""
                },
                {
                    "text": "Increase teacher salaries and training programs",
                    "option_img_link": ""
                }
            ],
            "consequences": [
                {
                    "text": "Better technical workforce but arts suffer",
                    "consequence_img_link": ""
                },
                {
                    "text": "Improved teaching quality but higher costs",
                    "consequence_img_link": ""
                }
            ]
        }
    ]
