
"""Read-only Canvas REST API transport for SyncCanvas.

Uses GET requests only. Never imports or changes legacy CanvasSync.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from synccanvas.services.canvas_reader import CanvasReadError


class CanvasHTTP:
    def __init__(
        self,
        base_url: str,
        token: str,
        opener: Callable | None = None,
        timeout: float = 15.0,
        max_pages: int = 20,
        max_retries: int = 2,
        retry_delay: float = 0.2,
        sleeper: Callable | None = None,
    ):
        base_url = base_url.strip().rstrip("/")
        parsed = urlsplit(base_url)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("Canvas URL must be an HTTPS site origin.")

        if not isinstance(token, str) or not token.strip():
            raise ValueError("Canvas token is required.")

        if timeout <= 0 or max_pages < 1 or max_retries < 0 or retry_delay < 0:
            raise ValueError("Invalid Canvas request limits.")

        self.base_url = base_url
        self._token = token.strip()
        self._opener = opener or urlopen
        self.timeout = timeout
        self.max_pages = max_pages
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._sleep = sleeper or time.sleep

    def _validate_url(self, url: str) -> None:
        parsed = urlsplit(url)
        origin = urlsplit(self.base_url)

        if (
            parsed.scheme != "https"
            or parsed.netloc != origin.netloc
            or parsed.username
            or parsed.password
            or not parsed.path.startswith("/api/v1/")
        ):
            raise CanvasReadError("Unsafe Canvas pagination URL.")

    @staticmethod
    def _next_page(headers, current_url: str) -> str | None:
        link_header = headers.get("Link", "")

        for entry in link_header.split(","):
            parts = entry.strip().split(";")
            if len(parts) < 2:
                continue

            relations = [
                part.strip()
                for part in parts[1:]
            ]

            if not any(
                relation in ('rel="next"', "rel=next")
                for relation in relations
            ):
                continue

            target = parts[0].strip()
            if not (target.startswith("<") and target.endswith(">")):
                raise CanvasReadError("Invalid Canvas pagination link.")

            return urljoin(current_url, target[1:-1])

        return None

    def get_list(self, path: str) -> list[dict]:
        """Fetch all pages of a Canvas list endpoint."""
        if not path.startswith("/api/v1/"):
            raise ValueError("Only Canvas API paths are supported.")

        next_url = self.base_url + path
        visited = set()
        results = []

        for _ in range(self.max_pages):
            self._validate_url(next_url)

            if next_url in visited:
                raise CanvasReadError("Canvas pagination loop detected.")
            visited.add(next_url)

            request = Request(
                next_url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                },
                method="GET",
            )

            # Retry only read-only GET requests and transient failures.
            for attempt in range(self.max_retries + 1):
                try:
                    with self._opener(request, timeout=self.timeout) as response:
                        payload = json.load(response)
                        following = self._next_page(response.headers, next_url)
                    break
                except HTTPError as exc:
                    if exc.code in (401, 403):
                        raise CanvasReadError("Canvas access was denied. Check the connection.") from None
                    if exc.code not in (408, 429, 500, 502, 503, 504):
                        raise CanvasReadError("Canvas could not complete the request.") from None
                    if attempt == self.max_retries:
                        message = ("Canvas is limiting requests. Try again later."
                                   if exc.code == 429 else "Canvas could not complete the request; temporarily unavailable. Try again later.")
                        raise CanvasReadError(message) from None
                except (URLError, OSError, TimeoutError):
                    if attempt == self.max_retries:
                        raise CanvasReadError("Canvas could not be reached. Your saved tasks are still available.") from None
                except (ValueError, TypeError):
                    raise CanvasReadError("Canvas returned invalid data. Your saved tasks are still available.") from None
                logging.getLogger("synccanvas.reliability").warning(
                    "canvas_retry attempt=%d max_attempts=%d", attempt + 2, self.max_retries + 1
                )
                self._sleep(self.retry_delay * (2 ** attempt))

            if not isinstance(payload, list):
                raise CanvasReadError(
                    "Canvas returned an unexpected response."
                )

            if not all(isinstance(item, dict) for item in payload):
                raise CanvasReadError(
                    "Canvas returned invalid list entries."
                )

            results.extend(payload)

            if following is None:
                return results

            next_url = following

        raise CanvasReadError(
            "Canvas returned more pages than the configured limit."
        )

    def assignments_for_course(self, course_id: int) -> list[dict]:
        if (
            isinstance(course_id, bool)
            or not isinstance(course_id, int)
            or course_id <= 0
        ):
            raise CanvasReadError("Invalid Canvas course ID.")

        return self.get_list(
            f"/api/v1/courses/{course_id}/assignments?per_page=100&include[]=submission"
        )
