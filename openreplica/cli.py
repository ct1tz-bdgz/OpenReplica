"""Command-line interface for OpenReplica."""

import asyncio
import uvicorn
import click
from openreplica.core.config import settings
from openreplica.core.logger import logger


@click.group()
def cli():
    """OpenReplica CLI - A beautiful replica of OpenHands."""
    pass


@cli.command()
@click.option("--host", default=settings.host, help="Host to bind to")
@click.option("--port", default=settings.port, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", default=1, help="Number of worker processes")
def serve(host: str, port: int, reload: bool, workers: int):
    """Start the OpenReplica server."""
    logger.info("Starting OpenReplica server", host=host, port=port)
    
    uvicorn.run(
        "openreplica.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_config=None  # Use our custom logging
    )


@cli.command()
def version():
    """Show version information."""
    from openreplica import __version__
    click.echo(f"OpenReplica v{__version__}")


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
