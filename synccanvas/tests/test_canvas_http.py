
"""Tests for the read-only Canvas HTTP transport."""

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from synccanvas.services.canvas_http import CanvasHTTP
from synccanvas.services.canvas_reader import (
    CanvasReadError,
    CanvasReader,
)


BASE = "https://school.instructure.com"


class FakeResponse(io.BytesIO):
    def __init__(self, payload, link=""):
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.headers = {"Link": link}


def make_client(opener, **kwargs):
    return CanvasHTTP(BASE, "fake-test-token", opener=opener, **kwargs)


def test_requires_https():
    with pytest.raises(ValueError):
        CanvasHTTP("http://school.instructure.com", "token")


def test_requires_token():
    with pytest.raises(ValueError):
        CanvasHTTP(BASE, "")


def test_rejects_url_with_credentials():
    with pytest.raises(ValueError):
        CanvasHTTP("https://user:pass@school.instructure.com", "token")


def test_get_assignments_uses_get_and_bearer_token():
    requests = []

    def opener(request, timeout):
        requests.append(request)
        return FakeResponse([{"id": 12, "name": "Homework"}])

    result = make_client(opener).assignments_for_course(7)

    assert len(result) == 1
    assert requests[0].get_method() == "GET"
    assert requests[0].get_header("Authorization") == "Bearer fake-test-token"
    assert "/courses/7/assignments" in requests[0].full_url


def test_pagination():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)

        if len(calls) == 1:
            return FakeResponse(
                [{"id": 1, "name": "First"}],
                f'<{BASE}/api/v1/courses/7/assignments?page=2>; rel="next"',
            )

        return FakeResponse([{"id": 2, "name": "Second"}])

    result = make_client(opener).assignments_for_course(7)

    assert [item["id"] for item in result] == [1, 2]
    assert len(calls) == 2


def test_rejects_external_pagination():
    def opener(request, timeout):
        return FakeResponse(
            [],
            '<https://attacker.example/steal>; rel="next"',
        )

    with pytest.raises(CanvasReadError, match="Unsafe"):
        make_client(opener).assignments_for_course(7)


def test_pagination_loop():
    def opener(request, timeout):
        return FakeResponse(
            [],
            f'<{request.full_url}>; rel="next"',
        )

    with pytest.raises(CanvasReadError, match="loop"):
        make_client(opener).assignments_for_course(7)


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "denied"),
        (403, "denied"),
        (429, "limiting"),
        (500, "complete"),
    ],
)
def test_http_errors(status, expected):
    def opener(request, timeout):
        raise HTTPError(
            request.full_url,
            status,
            "SECRET_TOKEN_SHOULD_NOT_APPEAR",
            {},
            None,
        )

    with pytest.raises(CanvasReadError) as error:
        make_client(opener).assignments_for_course(7)

    assert expected in str(error.value)
    assert "SECRET_TOKEN_SHOULD_NOT_APPEAR" not in str(error.value)


def test_network_failure():
    def opener(request, timeout):
        raise URLError("SECRET_TOKEN_SHOULD_NOT_APPEAR")

    with pytest.raises(CanvasReadError) as error:
        make_client(opener).assignments_for_course(7)

    assert "SECRET_TOKEN_SHOULD_NOT_APPEAR" not in str(error.value)


def test_rejects_non_list_response():
    def opener(request, timeout):
        return FakeResponse({"error": "unexpected"})

    with pytest.raises(CanvasReadError):
        make_client(opener).assignments_for_course(7)


def test_rejects_invalid_course_id():
    with pytest.raises(CanvasReadError):
        make_client(lambda *_args, **_kwargs: None).assignments_for_course(0)


def test_reader_integration():
    def opener(request, timeout):
        return FakeResponse(
            [{"id": 123, "name": "Science project", "due_at": None}]
        )

    transport = make_client(opener)
    reader = CanvasReader(transport.assignments_for_course)

    assignments = reader.assignments_for_course(7)

    assert len(assignments) == 1
    assert assignments[0].title == "Science project"
    assert assignments[0].course_id == 7


def test_page_limit():
    def opener(request, timeout):
        return FakeResponse(
            [],
            f'<{BASE}/api/v1/courses/7/assignments?page=2>; rel="next"',
        )

    with pytest.raises(CanvasReadError, match="page"):
        make_client(opener, max_pages=1).assignments_for_course(7)
