import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_get_initial_events_structure():
    response = client.get("/get_initial_events")
    assert response.status_code == 200
    events = response.json()

    assert isinstance(events, list)
    assert len(events) == 4

    for event in events:
        # Check top-level fields
        assert all(field in event for field in ["title", "image", "date", "options", "consequences"])
        assert isinstance(event["title"], str)
        assert isinstance(event["image"], str)
        assert isinstance(event["date"], str)

        # Check options
        assert isinstance(event["options"], list)
        assert len(event["options"]) == 2
        for option in event["options"]:
            assert all(field in option for field in ["title", "img"])
            assert isinstance(option["title"], str)
            assert isinstance(option["img"], str)

        # Check consequences
        assert isinstance(event["consequences"], list)
        assert len(event["consequences"]) == 2
        for consequence in event["consequences"]:
            assert all(field in consequence for field in ["text"])
            assert isinstance(consequence["text"], str)

def test_event_content():
    response = client.get("/get_initial_events")
    events = response.json()
