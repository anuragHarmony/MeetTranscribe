"""CLI for MeetTranscribe."""

import asyncio
import json
import logging
import sys
from typing import Optional

import click

from src.core.config import Config, get_config
from src.transcription.service import TranscriptionService


def setup_logging(verbose: bool = False):
    """Setup logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@click.group()
@click.option("--config", type=click.Path(exists=True), help="Config file path")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """MeetTranscribe - State-of-the-art meeting transcription."""
    setup_logging(verbose)

    # Load config
    if config:
        ctx.obj = Config.from_yaml(config)
    else:
        ctx.obj = get_config()


@cli.command()
@click.option(
    "--mode",
    type=click.Choice(["mic", "combined"]),
    default="combined",
    help="Capture mode",
)
@click.option("--output", type=click.Path(), help="Output file (JSON)")
@click.pass_obj
def record_local(config: Config, mode: str, output: Optional[str]):
    """Record and transcribe local audio."""
    click.echo(f"Starting local recording (mode: {mode})")

    async def run():
        service = TranscriptionService(config)
        await service.initialize()

        results = []

        try:
            async for result in service.start_local_recording(mode):
                # Print to console
                for segment in result["segments"]:
                    speaker = segment.get("speaker_name") or segment.get(
                        "speaker_id", "Unknown"
                    )
                    click.echo(f"[{speaker}] {segment['text']}")

                results.append(result)

        except KeyboardInterrupt:
            click.echo("\nStopping...")
        finally:
            await service.stop()

        # Save to file if requested
        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            click.echo(f"\nResults saved to {output}")

    asyncio.run(run())


@cli.command()
@click.option(
    "--platform",
    type=click.Choice(["google_meet", "zoom", "teams", "slack"]),
    required=True,
    help="Meeting platform",
)
@click.option("--url", required=True, help="Meeting URL")
@click.option("--email", help="Login email")
@click.option("--password", help="Login password")
@click.option("--output", type=click.Path(), help="Output file (JSON)")
@click.pass_obj
def record_meeting(
    config: Config,
    platform: str,
    url: str,
    email: Optional[str],
    password: Optional[str],
    output: Optional[str],
):
    """Join and transcribe online meeting."""
    click.echo(f"Joining {platform} meeting: {url}")

    credentials = None
    if email and password:
        credentials = {"email": email, "password": password}

    async def run():
        service = TranscriptionService(config)
        await service.initialize()

        results = []

        try:
            async for result in service.start_online_meeting(
                platform, url, credentials
            ):
                # Print to console
                for segment in result["segments"]:
                    speaker = segment.get("speaker_name") or segment.get(
                        "speaker_id", "Unknown"
                    )
                    click.echo(f"[{speaker}] {segment['text']}")

                results.append(result)

        except KeyboardInterrupt:
            click.echo("\nStopping...")
        finally:
            await service.stop()

        # Save to file if requested
        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            click.echo(f"\nResults saved to {output}")

    asyncio.run(run())


@cli.command()
@click.pass_obj
def list_profiles(config: Config):
    """List all voice profiles."""
    async def run():
        service = TranscriptionService(config)
        await service.initialize()

        profiles = await service.storage.get_all_profiles()

        if not profiles:
            click.echo("No voice profiles found")
            return

        click.echo(f"\nFound {len(profiles)} voice profiles:\n")
        for profile in profiles:
            click.echo(f"ID: {profile.profile_id}")
            click.echo(f"Name: {profile.name}")
            click.echo(f"Email: {profile.email}")
            click.echo(f"Samples: {profile.sample_count}")
            click.echo(f"Created: {profile.created_at}")
            click.echo()

    asyncio.run(run())


@cli.command()
@click.option("--profile-id", required=True, help="Profile ID to delete")
@click.pass_obj
def delete_profile(config: Config, profile_id: str):
    """Delete a voice profile."""
    async def run():
        service = TranscriptionService(config)
        await service.initialize()

        # Check if exists
        profile = await service.storage.get_profile(profile_id)
        if not profile:
            click.echo(f"Profile not found: {profile_id}")
            return

        # Confirm
        if click.confirm(f"Delete profile '{profile.name}' ({profile_id})?"):
            await service.storage.delete_profile(profile_id)
            click.echo("Profile deleted")
        else:
            click.echo("Cancelled")

    asyncio.run(run())


@cli.command()
def serve():
    """Start API server."""
    import uvicorn
    from src.api.app import app

    config = get_config()
    click.echo(f"Starting API server on {config.api.host}:{config.api.port}")

    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        workers=config.api.workers,
    )


if __name__ == "__main__":
    cli()
