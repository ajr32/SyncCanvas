from fastapi.testclient import TestClient
from synccanvas.main import app
from synccanvas.pages import labeled_input, layout


def test_navigation_has_landmark_and_skip_link():
    body = layout('Test', '<p>Hello</p>').body.decode()
    assert 'href="#main-content"' in body
    assert '<main id="main-content">' in body
    assert 'aria-label="Main navigation"' in body


def test_responsive_rules_and_focus_targets():
    body = layout('Test', '').body.decode()
    assert '@media(max-width:420px)' in body
    assert '@media(max-width:760px)' in body
    assert 'textarea:focus-visible' in body
    assert 'prefers-reduced-motion' in body


def test_reusable_form_control_escapes_attributes():
    field = labeled_input('Task <name>', 'task_title', value='" onfocus="bad', required=True)
    assert 'for="field-task_title"' in field
    assert 'id="field-task_title"' in field
    assert 'Task &lt;name&gt;' in field
    assert '&quot; onfocus=&quot;bad' in field
    assert ' required>' in field


def test_browser_not_found_is_readable_and_retains_404():
    response = TestClient(app).get('/a-page-that-does-not-exist', headers={'accept': 'text/html'})
    assert response.status_code == 404
    assert 'Page not found' in response.text
    assert 'Return to student home' in response.text


def test_api_not_found_remains_json():
    response = TestClient(app).get('/a-page-that-does-not-exist', headers={'accept': 'application/json'})
    assert response.status_code == 404
    assert response.json()['detail'] == 'Not Found'
