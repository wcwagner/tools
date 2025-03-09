"""Convert PDF files or URLs to markdown using Mistral's OCR API."""
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "mistralai",
#     "click",
#     "structlog",
# ]
# ///


import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import click
import structlog
import structlog.stdlib
from mistralai import DocumentURLChunk, Mistral
from mistralai.models import OCRResponse

# Configure structured logging
logging.basicConfig(format="%(message)s", level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()


def validate_api_key(api_key: str | None) -> str:
    """Validate the API key from environment variable or CLI argument."""
    if api_key:
        return api_key

    env_key = os.environ.get("MISTRAL_API_KEY")
    if env_key:
        return env_key

    log.error("API key is required. Please provide it with --api-key or set MISTRAL_API_KEY environment variable.")
    sys.exit(1)


def is_url(path_or_url: str) -> bool:
    """Check if the given string is a URL."""
    parsed = urlparse(path_or_url)
    return bool(parsed.scheme and parsed.netloc)


def process_url(
    client: Mistral,
    url: str,
    *,
    include_images: bool,
    log: structlog.BoundLogger,
) -> OCRResponse:
    """Process a URL using Mistral OCR API."""
    log.info("Processing URL", url=url)
    return client.ocr.process(
        model="mistral-ocr-latest",
        document=DocumentURLChunk(document_url=url),
        include_image_base64=include_images,
    )


def process_file(
    client: Mistral,
    file_path: Path,
    *,
    include_images: bool,
    log: structlog.BoundLogger,
) -> OCRResponse:
    """Process a local file using Mistral OCR API."""
    log.info("Processing file", file_path=str(file_path))

    # Upload the file for OCR processing
    start_time = time.time()
    uploaded_file = client.files.upload(
        file={
            "file_name": file_path.stem,
            "content": file_path.read_bytes(),
        },
        purpose="ocr",
    )
    log.debug("File uploaded", file_id=uploaded_file.id, duration=f"{time.time() - start_time:.2f}s")

    # Get a signed URL for the uploaded file
    start_time = time.time()
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=60)
    log.debug("Signed URL obtained", duration=f"{time.time() - start_time:.2f}s")

    # Process the file with OCR
    start_time = time.time()
    response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=include_images,
    )
    log.debug("OCR processing completed", duration=f"{time.time() - start_time:.2f}s")

    return response


def replace_images_in_markdown(markdown_str: str, images_dict: dict[str, str]) -> str:
    """Replace image placeholders with base64 encoded images in markdown."""
    for img_name, base64_data in images_dict.items():
        markdown_str = markdown_str.replace(
            f"![{img_name}]({img_name})",
            f"![{img_name}]({base64_data})",
        )
    return markdown_str


def generate_markdown(ocr_response: OCRResponse, *, include_images: bool) -> str:
    """Generate markdown from OCR response."""
    markdowns = []

    for page in ocr_response.pages:
        page_markdown = page.markdown

        if include_images:
            # Create a dictionary of image IDs to base64 strings
            image_data = {}
            for img in page.images:
                if img.image_base64:
                    image_data[img.id] = img.image_base64

            # Replace image references with base64 data URLs
            if image_data:
                page_markdown = replace_images_in_markdown(page_markdown, image_data)

        markdowns.append(page_markdown)

    return "\n\n---\n\n".join(markdowns)  # Add page separators


@click.command()
@click.argument(
    "input_path",
    type=str,
    required=True,
)
@click.option(
    "--output", "-o",
    type=click.Path(writable=True),
    help="Output markdown file path. If not provided, will use the input filename with .md extension.",
)
@click.option(
    "--api-key", "-k",
    help="Mistral API key. If not provided, will use MISTRAL_API_KEY environment variable.",
)
@click.option(
    "--inline-images/--no-inline-images",
    default=True,
    help="Include images inline as base64 encoded data URLs. Default: True",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    input_path: str,
    output: str | None,
    api_key: str | None,
    *,
    inline_images: bool = True,
    verbose: bool = False,
) -> None:
    """Convert a PDF file or URL to markdown using Mistral's OCR API.

    INPUT_PATH can be either a local PDF file path or a URL pointing to a PDF.
    """
    # Configure logging level
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger().setLevel(log_level)

    logger = log.bind()
    logger.info("Starting PDF to markdown conversion")

    # Validate API key
    api_key = validate_api_key(api_key)
    client = Mistral(api_key=api_key)

    # Process input based on whether it's a URL or file
    try:
        if is_url(input_path):
            ocr_response = process_url(client, input_path, include_images=inline_images, log=logger)
            # Default output name for URLs
            if not output:
                parsed_url = urlparse(input_path)
                filename = Path(parsed_url.path).name or "output"
                if "." in filename:
                    filename = filename.rsplit(".", 1)[0]
                output = f"{filename}.md"
        else:
            file_path = Path(input_path)
            if not file_path.exists():
                logger.error("File not found", file_path=str(file_path))
                sys.exit(1)

            ocr_response = process_file(client, file_path, include_images=inline_images, log=logger)

            # Default output name for files
            if not output:
                output = f"{file_path.stem}.md"

        # Generate markdown from OCR response
        logger.info("Generating markdown")
        markdown_content = generate_markdown(ocr_response, include_images=inline_images)

        # Write to output file
        output_path = Path(output)
        output_path.write_text(markdown_content)
        logger.info("Markdown file created", output_path=str(output_path))

    except Exception as e:
        logger.exception("Error occurred", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
