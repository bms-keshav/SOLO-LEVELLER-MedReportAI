"""
Utility functions for file processing and data formatting
"""
import io
import logging
from pathlib import Path
from typing import Optional

import PyPDF2
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text content from PDF file

    Args:
        file_bytes: PDF file as bytes

    Returns:
        Extracted text content
    """
    try:
        pdf_file = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text() or ""
            text += page_text

        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def validate_image(file_bytes: bytes) -> bool:
    """
    Validate if file is a valid image

    Args:
        file_bytes: Image file as bytes

    Returns:
        True if valid image, False otherwise
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        return True
    except Exception:
        return False


def normalize_parameter_name(name: str) -> str:
    """
    Normalize parameter name for lookup in reference ranges

    Args:
        name: Original parameter name

    Returns:
        Normalized parameter name (lowercase, underscores)
    """
    return name.lower().strip().replace(" ", "_").replace("-", "_")


def parse_numeric_value(value: str) -> Optional[float]:
    """
    Parse numeric value from string, handling common formats.

    Provides robust validation to prevent crashes from invalid input.

    Args:
        value: Value as string (e.g., "11.2", "<5.0", ">100")

    Returns:
        Numeric value or None if parsing fails
    """
    try:
        if value is None:
            logger.warning("Cannot parse None value")
            return None

        if not isinstance(value, str):
            value = str(value)

        if not value.strip():
            logger.warning("Cannot parse empty string")
            return None

        clean_value = value.strip()
        clean_value = clean_value.replace("<", "").replace(">", "").replace("~", "")
        clean_value = clean_value.replace("+-", "").replace("approx", "").replace("about", "")
        clean_value = clean_value.strip()

        if not clean_value:
            logger.warning(f"Value '{value}' became empty after cleaning")
            return None

        parsed_value = float(clean_value)

        if parsed_value != parsed_value:
            logger.warning(f"Parsed value is NaN from input: {value}")
            return None

        if parsed_value == float("inf") or parsed_value == float("-inf"):
            logger.warning(f"Parsed value is infinity from input: {value}")
            return None

        if parsed_value < 0:
            logger.warning(f"Parsed negative value {parsed_value} from input: {value}")

        if abs(parsed_value) > 1e10:
            logger.warning(f"Parsed extremely large value {parsed_value} from input: {value}")
            return None

        return parsed_value

    except ValueError as e:
        logger.warning(f"Could not parse numeric value '{value}': {str(e)}")
        return None
    except AttributeError as e:
        logger.warning(f"Attribute error parsing value '{value}': {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing value '{value}': {str(e)}")
        return None


def format_reference_range(min_val: float, max_val: float, unit: str) -> str:
    """
    Format reference range for display with validation.

    Args:
        min_val: Minimum value
        max_val: Maximum value
        unit: Unit of measurement

    Returns:
        Formatted string (e.g., "12.0 - 16.0 g/dL")
    """
    try:
        if min_val is None or max_val is None:
            logger.warning("Cannot format reference range: min or max is None")
            return "Reference range unavailable"

        try:
            min_val = float(min_val)
            max_val = float(max_val)
        except (ValueError, TypeError) as e:
            logger.warning(f"Cannot convert range values to float: {e}")
            return "Reference range unavailable"

        if not unit or not isinstance(unit, str):
            unit = ""
        else:
            unit = str(unit).strip()

        if max_val >= 999:
            return f">= {min_val} {unit}".strip()

        return f"{min_val} - {max_val} {unit}".strip()

    except Exception as e:
        logger.error(f"Unexpected error formatting reference range: {e}")
        return "Reference range unavailable"


def determine_file_type(filename: str) -> str:
    """
    Determine file type from filename

    Args:
        filename: Name of the file

    Returns:
        File type: 'pdf', 'image', or 'unknown'
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return "pdf"
    if suffix in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
        return "image"
    return "unknown"
