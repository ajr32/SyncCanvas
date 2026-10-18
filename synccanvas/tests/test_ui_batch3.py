"""Smoke tests for the combined UI batch."""
from fastapi.testclient import TestClient
from synccanvas.main import app


def test_new_ui_routes_render():
    with TestClient(app) as client:
        for path, label in [('/add', 'Add Information'), ('/review', 'School Check-Out'), ('/afternoon', 'My Afternoon'), ('/parent', 'Parent Review'), ('/settings', 'Settings')]:
            response = client.get(path)
            assert response.status_code == 200
            assert label in response.text


def test_school_checkout_is_a_simple_class_double_check():
    with TestClient(app) as client:
        response = client.get('/review')
        assert 'Did you write down everything' in response.text
        assert 'Ready-to-go checklist' not in response.text
