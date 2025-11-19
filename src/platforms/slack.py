"""Slack Huddle integration."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from src.core.config import PlatformConfig
from src.core.interfaces import MeetingMetadata, MeetingPlatform
from src.platforms.base import BasePlatformIntegration

logger = logging.getLogger(__name__)


class SlackIntegration(BasePlatformIntegration):
    """Slack Huddle platform integration."""

    def __init__(self, config: PlatformConfig):
        """Initialize Slack integration."""
        super().__init__(config, MeetingPlatform.SLACK_HUDDLE)

    async def connect(
        self, meeting_url: str, credentials: Optional[Dict[str, str]] = None
    ) -> None:
        """Connect to Slack Huddle."""
        if self._is_connected:
            logger.warning("Already connected to a huddle")
            return

        logger.info(f"Connecting to Slack Huddle: {meeting_url}")

        await self._launch_browser()
        await self._page.goto(meeting_url, wait_until="networkidle")

        if credentials:
            await self._login(credentials)

        await asyncio.sleep(2)

        # Slack huddles are typically accessed through workspace
        # This is a simplified implementation
        meeting_id = "slack_huddle_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        self._metadata = MeetingMetadata(
            meeting_id=meeting_id,
            platform=MeetingPlatform.SLACK_HUDDLE,
            title=None,
            start_time=datetime.now(),
            end_time=None,
            participants=[],
        )

        self._is_connected = True
        logger.info("Connected to Slack Huddle")
        asyncio.create_task(self._capture_audio())

    async def _login(self, credentials: Dict[str, str]) -> None:
        """Login to Slack workspace."""
        email = credentials.get("email")
        password = credentials.get("password")

        if not email or not password:
            return

        try:
            email_input = await self._page.wait_for_selector(
                'input[type="email"]', timeout=5000
            )
            await email_input.fill(email)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(2)

            password_input = await self._page.wait_for_selector(
                'input[type="password"]', timeout=5000
            )
            await password_input.fill(password)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Login failed: {e}")
