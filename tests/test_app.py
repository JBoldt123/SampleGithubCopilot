"""
Tests for the Mergington High School API (src/app.py).

Coverage: all 4 endpoints, every branch.
Pattern: AAA (Arrange - Act - Assert) throughout.
"""

import copy

import pytest
from starlette.testclient import TestClient

from src.app import activities, app

# ---------------------------------------------------------------------------
# Module-level snapshot captured once, before any test mutates the dict
# ---------------------------------------------------------------------------
_ORIGINAL_ACTIVITIES = copy.deepcopy(activities)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    """Return a Starlette TestClient wrapping the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Restore the in-memory activities dict to its original state before each test."""
    activities.clear()
    activities.update(copy.deepcopy(_ORIGINAL_ACTIVITIES))
    yield
    activities.clear()
    activities.update(copy.deepcopy(_ORIGINAL_ACTIVITIES))


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root_redirects_to_static_index(self, client):
        # Arrange – no setup needed; endpoint takes no parameters

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert response.headers["location"].endswith("/static/index.html")


# ---------------------------------------------------------------------------
# GET /activities
# ---------------------------------------------------------------------------

class TestGetActivities:
    def test_get_activities_returns_200(self, client):
        # Arrange – no setup needed

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200

    def test_get_activities_returns_all_activities(self, client):
        # Arrange
        expected_names = {
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Art Studio",
            "Drama Club",
            "Debate Team",
            "Science Club",
        }

        # Act
        response = client.get("/activities")

        # Assert
        assert set(response.json().keys()) == expected_names

    def test_get_activities_activity_schema(self, client):
        # Arrange
        required_keys = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")

        # Assert – every activity must expose the full schema
        for name, activity in response.json().items():
            assert required_keys == set(activity.keys()), (
                f"Activity '{name}' is missing keys"
            )


# ---------------------------------------------------------------------------
# POST /activities/{activity_name}/signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_signup_success(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert email in body["message"]
        assert activity_name in body["message"]
        assert email in activities[activity_name]["participants"]

    def test_signup_activity_not_found(self, client):
        # Arrange
        activity_name = "Underwater Basket Weaving"
        email = "student@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_already_signed_up(self, client):
        # Arrange – michael@mergington.edu is already seeded into Chess Club
        activity_name = "Chess Club"
        email = "michael@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"

    def test_signup_activity_full(self, client):
        # Arrange – fill Tennis Club (max_participants=10) to capacity
        activity_name = "Tennis Club"
        filler_emails = [f"filler{i}@mergington.edu" for i in range(9)]
        activities[activity_name]["participants"] = (
            activities[activity_name]["participants"] + filler_emails
        )
        assert len(activities[activity_name]["participants"]) == activities[activity_name]["max_participants"]

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "onemore@mergington.edu"},
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Activity is full"


# ---------------------------------------------------------------------------
# DELETE /activities/{activity_name}/signup
# ---------------------------------------------------------------------------

class TestUnregister:
    def test_unregister_success(self, client):
        # Arrange – michael@mergington.edu is seeded in Chess Club
        activity_name = "Chess Club"
        email = "michael@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert email in body["message"]
        assert activity_name in body["message"]
        assert email not in activities[activity_name]["participants"]

    def test_unregister_activity_not_found(self, client):
        # Arrange
        activity_name = "Underwater Basket Weaving"
        email = "student@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_student_not_signed_up(self, client):
        # Arrange – this email is not enrolled in Chess Club
        activity_name = "Chess Club"
        email = "nothere@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not signed up for this activity"
