import pytest
from synccanvas.canvas_settings import CanvasSettings, SettingsError, get_settings, read_env_file

def test_empty_canvas_is_allowed():
    assert CanvasSettings().url == ""

@pytest.mark.parametrize("url,token", [
    ("http://canvas.example.com", "token"),
    ("https://canvas.example.com/api", "token"),
    ("https://canvas.example.com/?key=1", "token"),
    ("https://canvas.example.com", ""),
    ("", "token"),
])
def test_invalid_settings(url, token):
    with pytest.raises(SettingsError):
        CanvasSettings(url=url, token=token)

def test_environment_overrides_file(tmp_path):
    path = tmp_path / ".env"
    path.write_text("SYNCCANVAS_CANVAS_URL=https://school.instructure.com\nSYNCCANVAS_CANVAS_TOKEN=old\n")
    assert get_settings({"SYNCCANVAS_CANVAS_TOKEN": "new"}, path).token == "new"

def test_other_env_keys_ignored(tmp_path):
    path = tmp_path / ".env"
    path.write_text("OTHER_SECRET=secret\n")
    assert read_env_file(path) == {}
