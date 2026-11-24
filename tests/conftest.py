from datetime import datetime

import pytest

from goup.web import create_app


@pytest.fixture
def now():
    return datetime(2026, 11, 24, 12)


@pytest.fixture
def profile(now):
    return {"name": "Student", "district": "Mapo-gu", "body_weight": 75,
            "lifts": {}, "joined_at": now.isoformat()}


@pytest.fixture
def client(tmp_path, now):
    app = create_app(tmp_path / "workouts.json", lambda: now)
    app.testing = True
    return app.test_client()
