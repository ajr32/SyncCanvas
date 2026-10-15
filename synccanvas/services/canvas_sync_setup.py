
"""Opt-in configuration of the SyncCanvas Canvas import worker.

No credentials are required at import time.
No network requests occur during configuration.
Legacy CanvasSync is never imported or modified.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from synccanvas.services.background_sync import BackgroundSync
from synccanvas.services.canvas_http import CanvasHTTP
from synccanvas.services.canvas_import_worker import CanvasImportWorker
from synccanvas.services.sync_coordinator import SyncCoordinator


class CanvasConfigurationError(ValueError):
    """Canvas configuration is incomplete or invalid."""


def build_canvas_coordinator(
    settings: Mapping[str, str] | None = None,
) -> SyncCoordinator:
    """Build an independent, explicitly configured sync coordinator.

    Required settings:
        SYNCCANVAS_CANVAS_URL
        SYNCCANVAS_CANVAS_TOKEN

    The returned coordinator is not automatically installed in the app.
    """
    if settings is None:
        settings = os.environ

    url = settings.get("SYNCCANVAS_CANVAS_URL", "").strip()
    token = settings.get("SYNCCANVAS_CANVAS_TOKEN", "").strip()

    if not url or not token:
        raise CanvasConfigurationError(
            "Canvas connection is not configured."
        )

    try:
        client = CanvasHTTP(
            base_url=url,
            token=token,
        )
    except ValueError as error:
        raise CanvasConfigurationError(
            "Canvas connection settings are invalid."
        ) from None

    worker = CanvasImportWorker(
        fetch_assignments=client.assignments_for_course,
    )

    return SyncCoordinator(
        background=BackgroundSync(worker=worker)
    )
