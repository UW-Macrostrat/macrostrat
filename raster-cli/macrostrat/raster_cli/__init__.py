from pathlib import Path

import typer

from .process import process_image

# See this code
# https://github.com/developmentseed/cogeo-watchbot

app = typer.Typer()


@app.command(name="process")
def _process_image(image: str, key: str = typer.Argument(None)):
    """Get an image from a URL or Path, convert to COG, and upload to S3"""
    process_image(image, key)


if __name__ == "__main__":
    app()
