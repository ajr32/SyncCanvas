"""Focused regression checks for issues #79, #80 and #108."""
from synccanvas.pages import layout, options


def test_keyboard_focus_and_touch_targets():
    page = layout('Test', '<button>Save</button>').body.decode()
    assert 'button:focus-visible' in page
    assert 'summary:focus-visible' in page
    assert 'min-height:44px' in page
    assert 'viewport' in page


def test_reduced_motion_respected():
    page = layout('Test', 'Content').body.decode()
    assert 'prefers-reduced-motion:reduce' in page


def test_optional_task_entry_is_collapsible():
    import inspect
    from synccanvas.pages import student
    source = inspect.getsource(student)
    assert '<details class="class-entry">' in source
    assert 'Add homework or a note' in source
    assert 'Nothing Tonight' in source
    assert 'Checked — still deciding' in source


def test_kind_selector_keeps_no_typing_choices():
    assert '<option' in options()
    assert 'value=' in options()
