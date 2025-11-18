"""
Playwright-based meeting bot for joining Google Meet, Zoom, Teams, etc.

This implementation uses browser automation to join meetings and capture audio.
Note: This is a basic implementation. Production use would require more robust
error handling and platform-specific optimizations.
"""

import logging
from typing import Optional, List, Callable
import asyncio
from datetime import datetime
import re

from .base import MeetingBotInterface, MeetingMetadata, ParticipantInfo

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    async_playwright = None

logger = logging.getLogger(__name__)


class PlaywrightMeetingBot(MeetingBotInterface):
    """
    Meeting bot using Playwright for browser automation

    Supports:
    - Google Meet
    - Zoom (web client)
    - Microsoft Teams (web client)
    - Slack Huddles

    Note: This is a reference implementation. For production use,
    consider using dedicated APIs or services like Recall.ai, MeetStream.ai
    """

    def __init__(self, headless: bool = False):
        """
        Initialize Playwright meeting bot

        Args:
            headless: Run browser in headless mode
        """
        if async_playwright is None:
            raise ImportError(
                "playwright is not installed. "
                "Install it with: pip install playwright && playwright install"
            )

        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.in_meeting = False
        self.meeting_metadata: Optional[MeetingMetadata] = None
        self.audio_callback: Optional[Callable] = None

    async def _init_browser(self):
        """Initialize Playwright browser"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()

        if self.browser is None:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--use-fake-ui-for-media-stream',  # Auto-allow mic/camera
                    '--use-fake-device-for-media-stream',
                    '--disable-blink-features=AutomationControlled'
                ]
            )

    def join_meeting(
        self,
        meeting_url: str,
        display_name: str = "MeetTranscribe Bot"
    ) -> MeetingMetadata:
        """
        Join meeting (synchronous wrapper)

        Args:
            meeting_url: Meeting URL
            display_name: Bot display name

        Returns:
            MeetingMetadata: Meeting information
        """
        return asyncio.run(self._join_meeting_async(meeting_url, display_name))

    async def _join_meeting_async(
        self,
        meeting_url: str,
        display_name: str
    ) -> MeetingMetadata:
        """
        Join meeting asynchronously

        Args:
            meeting_url: Meeting URL
            display_name: Bot display name

        Returns:
            MeetingMetadata: Meeting information
        """
        await self._init_browser()

        # Determine platform from URL
        platform = self._detect_platform(meeting_url)
        logger.info(f"Joining {platform} meeting: {meeting_url}")

        # Create new page
        context = await self.browser.new_context(
            permissions=['microphone', 'camera']
        )
        self.page = await context.new_page()

        # Join meeting based on platform
        if platform == "google_meet":
            await self._join_google_meet(meeting_url, display_name)
        elif platform == "zoom":
            await self._join_zoom(meeting_url, display_name)
        elif platform == "teams":
            await self._join_teams(meeting_url, display_name)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        # Extract meeting metadata
        self.meeting_metadata = await self._extract_metadata(platform, meeting_url)
        self.in_meeting = True

        return self.meeting_metadata

    def _detect_platform(self, url: str) -> str:
        """Detect meeting platform from URL"""
        url_lower = url.lower()

        if 'meet.google.com' in url_lower:
            return 'google_meet'
        elif 'zoom.us' in url_lower:
            return 'zoom'
        elif 'teams.microsoft.com' in url_lower or 'teams.live.com' in url_lower:
            return 'teams'
        elif 'slack.com' in url_lower:
            return 'slack'
        else:
            raise ValueError(f"Unknown meeting platform for URL: {url}")

    async def _join_google_meet(self, url: str, display_name: str):
        """Join Google Meet"""
        await self.page.goto(url)

        # Wait for page load
        await self.page.wait_for_load_state('networkidle')

        # Enter name if prompted
        try:
            name_input = await self.page.wait_for_selector(
                'input[placeholder*="name" i]',
                timeout=5000
            )
            if name_input:
                await name_input.fill(display_name)
        except Exception:
            pass

        # Turn off camera and microphone
        try:
            # Click camera button to turn off
            camera_btn = await self.page.query_selector('[data-is-muted="false"][aria-label*="camera" i]')
            if camera_btn:
                await camera_btn.click()

            # Microphone typically starts muted
        except Exception as e:
            logger.warning(f"Error toggling media: {e}")

        # Click "Join now" button
        try:
            join_button = await self.page.wait_for_selector(
                'button:has-text("Join"), button:has-text("Ask to join")',
                timeout=10000
            )
            await join_button.click()
            logger.info("Joined Google Meet")
        except Exception as e:
            logger.error(f"Failed to join Google Meet: {e}")
            raise

    async def _join_zoom(self, url: str, display_name: str):
        """Join Zoom meeting (web client)"""
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')

        # Click "Join from browser"
        try:
            browser_btn = await self.page.wait_for_selector(
                'a:has-text("Join from Your Browser")',
                timeout=5000
            )
            await browser_btn.click()
        except Exception:
            pass

        # Enter name
        try:
            name_input = await self.page.wait_for_selector(
                'input[name="name"], input#inputname',
                timeout=5000
            )
            await name_input.fill(display_name)
        except Exception as e:
            logger.warning(f"Name input not found: {e}")

        # Join meeting
        try:
            join_btn = await self.page.wait_for_selector(
                'button:has-text("Join")',
                timeout=5000
            )
            await join_btn.click()
            logger.info("Joined Zoom meeting")
        except Exception as e:
            logger.error(f"Failed to join Zoom: {e}")
            raise

    async def _join_teams(self, url: str, display_name: str):
        """Join Microsoft Teams meeting"""
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')

        # Click "Join on the web instead"
        try:
            web_btn = await self.page.wait_for_selector(
                'a:has-text("Join on the web")',
                timeout=5000
            )
            await web_btn.click()
        except Exception:
            pass

        # Enter name
        try:
            name_input = await self.page.wait_for_selector(
                'input[placeholder*="name" i]',
                timeout=5000
            )
            await name_input.fill(display_name)
        except Exception as e:
            logger.warning(f"Name input not found: {e}")

        # Join meeting
        try:
            join_btn = await self.page.wait_for_selector(
                'button:has-text("Join now")',
                timeout=5000
            )
            await join_btn.click()
            logger.info("Joined Teams meeting")
        except Exception as e:
            logger.error(f"Failed to join Teams: {e}")
            raise

    async def _extract_metadata(
        self,
        platform: str,
        meeting_url: str
    ) -> MeetingMetadata:
        """Extract meeting metadata"""
        # Extract meeting ID from URL
        meeting_id = self._extract_meeting_id(meeting_url)

        # Get participants (platform-specific)
        participants = await self._get_participants_async(platform)

        metadata = MeetingMetadata(
            meeting_id=meeting_id,
            platform=platform,
            meeting_url=meeting_url,
            start_time=datetime.now(),
            participants=participants
        )

        return metadata

    def _extract_meeting_id(self, url: str) -> str:
        """Extract meeting ID from URL"""
        # Google Meet: meet.google.com/abc-defg-hij
        match = re.search(r'meet\.google\.com/([a-z\-]+)', url)
        if match:
            return match.group(1)

        # Zoom: zoom.us/j/123456789
        match = re.search(r'zoom\.us/j/(\d+)', url)
        if match:
            return match.group(1)

        # Teams: teams ID
        match = re.search(r'teams\.(?:microsoft|live)\.com.*?/([a-zA-Z0-9\-]+)', url)
        if match:
            return match.group(1)

        # Fallback: use full URL
        return url

    async def _get_participants_async(self, platform: str) -> List[ParticipantInfo]:
        """Get participants from meeting (platform-specific)"""
        participants = []

        # This is a simplified implementation
        # In production, you'd need to parse the participant list from the UI
        # or use platform APIs

        try:
            if platform == "google_meet":
                # Google Meet shows participants count
                # Would need to click participants button and parse list
                pass
            # Similar for other platforms
        except Exception as e:
            logger.warning(f"Could not extract participants: {e}")

        return participants

    def leave_meeting(self) -> None:
        """Leave the current meeting"""
        asyncio.run(self._leave_meeting_async())

    async def _leave_meeting_async(self):
        """Leave meeting asynchronously"""
        if self.page:
            await self.page.close()
            self.page = None

        self.in_meeting = False
        logger.info("Left meeting")

    def get_audio_stream(self):
        """
        Get audio stream from meeting

        Note: Capturing audio from browser requires additional setup
        This is a placeholder implementation
        """
        logger.warning(
            "Browser audio capture requires additional configuration. "
            "Consider using system audio capture instead."
        )
        return None

    def get_participants(self) -> List[ParticipantInfo]:
        """Get current participants"""
        if self.meeting_metadata:
            return self.meeting_metadata.participants
        return []

    def is_in_meeting(self) -> bool:
        """Check if in meeting"""
        return self.in_meeting

    def set_audio_callback(self, callback: Callable) -> None:
        """Set audio callback"""
        self.audio_callback = callback

    async def cleanup(self):
        """Cleanup resources"""
        if self.page:
            await self.page.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

    def __del__(self):
        """Destructor"""
        if self.in_meeting:
            try:
                asyncio.run(self.cleanup())
            except Exception:
                pass
