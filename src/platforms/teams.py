"""Microsoft Teams integration."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from src.core.config import PlatformConfig
from src.core.interfaces import MeetingMetadata, MeetingPlatform
from src.platforms.base import BasePlatformIntegration

logger = logging.getLogger(__name__)


class TeamsIntegration(BasePlatformIntegration):
    """Microsoft Teams platform integration."""

    def __init__(self, config: PlatformConfig):
        """Initialize Teams integration."""
        super().__init__(config, MeetingPlatform.MICROSOFT_TEAMS)

    async def connect(
        self, meeting_url: str, credentials: Optional[Dict[str, str]] = None
    ) -> None:
        """Connect to Teams meeting."""
        if self._is_connected:
            logger.warning("Already connected to a meeting")
            return

        logger.info(f"Connecting to Microsoft Teams: {meeting_url}")

        await self._launch_browser()
        await self._page.goto(meeting_url, wait_until="networkidle")

        # Handle authentication if needed
        if credentials:
            await self._login(credentials)

        await asyncio.sleep(2)

        # Try to join anonymously or continue to meeting
        try:
            join_selectors = [
                'button[data-tid="prejoin-join-button"]',
                'text="Join now"',
                'text="Continue"',
            ]

            for selector in join_selectors:
                try:
                    button = await self._page.wait_for_selector(selector, timeout=5000)
                    if button:
                        await button.click()
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Could not find join button: {e}")

        meeting_id = meeting_url.split("/")[-1].split("?")[0]
        self._metadata = MeetingMetadata(
            meeting_id=meeting_id,
            platform=MeetingPlatform.MICROSOFT_TEAMS,
            title=None,
            start_time=datetime.now(),
            end_time=None,
            participants=[],
        )

        self._is_connected = True
        logger.info("Connected to Teams meeting")
        asyncio.create_task(self._capture_audio())

    async def _login(self, credentials: Dict[str, str]) -> None:
        """Login to Microsoft account."""
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
