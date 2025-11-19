"""Google Meet integration."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.core.config import PlatformConfig
from src.core.interfaces import MeetingMetadata, MeetingPlatform
from src.platforms.base import BasePlatformIntegration

logger = logging.getLogger(__name__)


class GoogleMeetIntegration(BasePlatformIntegration):
    """Google Meet platform integration."""

    def __init__(self, config: PlatformConfig):
        """Initialize Google Meet integration."""
        super().__init__(config, MeetingPlatform.GOOGLE_MEET)

    async def connect(
        self, meeting_url: str, credentials: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Connect to Google Meet.

        Args:
            meeting_url: Google Meet URL
            credentials: Optional credentials (email, password)
        """
        if self._is_connected:
            logger.warning("Already connected to a meeting")
            return

        logger.info(f"Connecting to Google Meet: {meeting_url}")

        await self._launch_browser()

        # Navigate to meeting
        await self._page.goto(meeting_url, wait_until="networkidle")

        # Handle login if credentials provided
        if credentials:
            await self._login(credentials)

        # Wait for meeting to load
        await asyncio.sleep(2)

        # Disable camera and mic prompts
        try:
            # Click "Join now" or similar button
            join_button_selectors = [
                'button[jsname="Qx7uuf"]',  # Join now button
                'div[jsname="Qx7uuf"]',
                'text="Join now"',
                'text="Ask to join"',
            ]

            for selector in join_button_selectors:
                try:
                    button = await self._page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if button:
                        await button.click()
                        break
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Could not find join button: {e}")

        # Extract metadata
        await self._extract_metadata(meeting_url)

        self._is_connected = True
        logger.info("Connected to Google Meet")

        # Start audio capture task
        asyncio.create_task(self._capture_audio())

    async def _login(self, credentials: Dict[str, str]) -> None:
        """Login to Google account."""
        email = credentials.get("email")
        password = credentials.get("password")

        if not email or not password:
            logger.warning("Credentials incomplete, skipping login")
            return

        try:
            # Enter email
            email_input = await self._page.wait_for_selector(
                'input[type="email"]', timeout=5000
            )
            await email_input.fill(email)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(2)

            # Enter password
            password_input = await self._page.wait_for_selector(
                'input[type="password"]', timeout=5000
            )
            await password_input.fill(password)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(3)

            logger.info("Logged in to Google account")
        except Exception as e:
            logger.error(f"Login failed: {e}")

    async def _extract_metadata(self, meeting_url: str) -> None:
        """Extract meeting metadata."""
        try:
            # Extract meeting ID from URL
            meeting_id = meeting_url.split("/")[-1].split("?")[0]

            # Try to get meeting title
            title = None
            try:
                title_element = await self._page.query_selector('div[jsname="rQC7Ie"]')
                if title_element:
                    title = await title_element.inner_text()
            except Exception:
                pass

            # Extract participants
            participants = await self._extract_participants()

            self._metadata = MeetingMetadata(
                meeting_id=meeting_id,
                platform=MeetingPlatform.GOOGLE_MEET,
                title=title,
                start_time=datetime.now(),
                end_time=None,
                participants=participants,
            )

            logger.info(f"Extracted metadata: {len(participants)} participants")
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            self._metadata = MeetingMetadata(
                meeting_id="unknown",
                platform=MeetingPlatform.GOOGLE_MEET,
                title=None,
                start_time=datetime.now(),
                end_time=None,
                participants=[],
            )

    async def _extract_participants(self) -> List[Dict[str, str]]:
        """Extract participant information."""
        participants = []

        try:
            # Click on participants button to open panel
            participant_button_selectors = [
                'button[aria-label*="participant"]',
                'button[aria-label*="People"]',
                'div[jsname="pXMxCb"]',
            ]

            for selector in participant_button_selectors:
                try:
                    button = await self._page.query_selector(selector)
                    if button:
                        await button.click()
                        await asyncio.sleep(1)
                        break
                except Exception:
                    continue

            # Extract participant names
            participant_elements = await self._page.query_selector_all(
                'div[jscontroller] span[jsname]'
            )

            for element in participant_elements:
                try:
                    name = await element.inner_text()
                    if name and len(name.strip()) > 0:
                        participants.append({
                            "name": name.strip(),
                            "email": "",  # Email not easily accessible in UI
                        })
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract participants: {e}")

        return participants[:50]  # Limit to 50 participants
