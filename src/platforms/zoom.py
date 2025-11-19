"""Zoom integration."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.core.config import PlatformConfig
from src.core.interfaces import MeetingMetadata, MeetingPlatform
from src.platforms.base import BasePlatformIntegration

logger = logging.getLogger(__name__)


class ZoomIntegration(BasePlatformIntegration):
    """Zoom platform integration."""

    def __init__(self, config: PlatformConfig):
        """Initialize Zoom integration."""
        super().__init__(config, MeetingPlatform.ZOOM)

    async def connect(
        self, meeting_url: str, credentials: Optional[Dict[str, str]] = None
    ) -> None:
        """Connect to Zoom meeting."""
        if self._is_connected:
            logger.warning("Already connected to a meeting")
            return

        logger.info(f"Connecting to Zoom: {meeting_url}")

        await self._launch_browser()
        await self._page.goto(meeting_url, wait_until="networkidle")

        # Handle name entry if required
        try:
            name_input = await self._page.wait_for_selector(
                'input[id="input-for-name"]', timeout=5000
            )
            if name_input:
                await name_input.fill(credentials.get("name", "Transcriber") if credentials else "Transcriber")
                join_button = await self._page.query_selector('button[type="submit"]')
                if join_button:
                    await join_button.click()
        except Exception as e:
            logger.warning(f"Name entry not required or failed: {e}")

        await asyncio.sleep(2)

        # Extract metadata
        meeting_id = meeting_url.split("/")[-1].split("?")[0]
        self._metadata = MeetingMetadata(
            meeting_id=meeting_id,
            platform=MeetingPlatform.ZOOM,
            title=None,
            start_time=datetime.now(),
            end_time=None,
            participants=[],
        )

        self._is_connected = True
        logger.info("Connected to Zoom meeting")
        asyncio.create_task(self._capture_audio())
