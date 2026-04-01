"""
Gemini API service for extracting structured lab values from reports

╔══════════════════════════════════════════════════════════════════════╗
║  CRITICAL ARCHITECTURAL RULE: NO MEDICAL CLASSIFICATION BY AI        ║
║                                                                       ║
║  This service ONLY extracts:                                         ║
║    ✓ Parameter names (e.g., "Hemoglobin")                           ║
║    ✓ Numeric values (e.g., "11.2")                                  ║
║    ✓ Units (e.g., "g/dL")                                           ║
║                                                                       ║
║  This service NEVER produces:                                        ║
║    ✗ Medical status (normal/high/low) - RULE ENGINE ONLY            ║
║    ✗ Medical interpretations                                         ║
║    ✗ Clinical recommendations                                        ║
║                                                                       ║
║  Design Decision: AI is for parsing unstructured data ONLY.         ║
║  Medical classification is ALWAYS done by deterministic rules.       ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import os
import json
import logging
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from models.schemas import ExtractedLabValue

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class GeminiExtractor:
    """
    Extracts structured lab values from medical reports using Gemini API.
    Uses strict JSON output for reliable parsing.

    ARCHITECTURAL BOUNDARY: This class does NOT and MUST NOT classify values
    as normal/high/low. It only extracts raw data from reports.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)

        model_name = self._select_model_name()

        # Configure model with JSON response format
        generation_config = {
            "temperature": 0.1,  # Low temperature for consistent output
            "response_mime_type": "application/json"
        }

        self.model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config
        )
        logger.info(f"GeminiExtractor initialized with model: {model_name}")

    def _select_model_name(self) -> str:
        """
        Select a model that is actually available for generateContent.

        Priority:
        1) GEMINI_MODEL env override
        2) Preferred models present in list_models()
        3) Any available model supporting generateContent
        """
        env_model = os.getenv("GEMINI_MODEL", "").strip()
        if env_model:
            logger.info(f"Using GEMINI_MODEL override: {env_model}")
            return env_model

        preferred_models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-1.5-pro-latest",
        ]

        try:
            available = []
            for model in genai.list_models():
                methods = set(getattr(model, "supported_generation_methods", []) or [])
                if "generateContent" not in methods:
                    continue

                model_name = getattr(model, "name", "")
                if model_name.startswith("models/"):
                    model_name = model_name.split("/", 1)[1]
                if model_name:
                    available.append(model_name)

            for preferred in preferred_models:
                if preferred in available:
                    return preferred

            if available:
                return available[0]

        except Exception as e:
            logger.warning(f"Could not list Gemini models dynamically: {e}")

        # Safe fallback that works on most current accounts.
        return "gemini-2.0-flash"

    def extract_from_image(self, image_bytes: bytes) -> List[ExtractedLabValue]:
        """
        Extract lab values from image file

        Args:
            image_bytes: Image file as bytes

        Returns:
            List of extracted lab values
        """
        try:
            # Detect image format (default to jpeg if unknown)
            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": image_bytes
                }
            ]

            prompt = self._get_extraction_prompt()

            response = self.model.generate_content([prompt, image_parts[0]])
            return self._parse_json_response(response.text)

        except Exception as e:
            logger.error(f"Gemini extraction from image failed: {str(e)}")
            # Try fallback extraction
            return self._fallback_extraction(str(e))

    def extract_from_pdf(self, pdf_bytes: bytes) -> List[ExtractedLabValue]:
        """
        Extract lab values from PDF bytes directly using Gemini multimodal input.

        This acts as a fallback for scanned PDFs where local text extraction
        returns little or no usable content.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            List of extracted lab values
        """
        try:
            pdf_part = {
                "mime_type": "application/pdf",
                "data": pdf_bytes
            }

            prompt = self._get_extraction_prompt()
            response = self.model.generate_content([prompt, pdf_part])
            return self._parse_json_response(response.text)

        except Exception as e:
            logger.error(f"Gemini extraction from PDF failed: {str(e)}")
            return self._fallback_extraction(str(e))

    def extract_from_text(self, text: str) -> List[ExtractedLabValue]:
        """
        Extract lab values from text content

        Args:
            text: Text content from report

        Returns:
            List of extracted lab values
        """
        try:
            prompt = self._get_extraction_prompt() + f"\n\nReport Text:\n{text}"

            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)

        except Exception as e:
            logger.error(f"Gemini extraction from text failed: {str(e)}")
            # Try deterministic regex fallback from raw text before failing.
            regex_results = self._extract_from_text_regex(text)
            if regex_results:
                logger.info(f"Regex fallback extracted {len(regex_results)} lab values")
                return regex_results

            return self._fallback_extraction(str(e))

    def _get_extraction_prompt(self) -> str:
        """
        Get the prompt for extraction with JSON schema

        ARCHITECTURAL NOTE: This prompt explicitly forbids the AI from making
        medical classifications. The AI is ONLY for data extraction.

        Returns:
            Extraction prompt with JSON schema
        """
        return """
You are a medical lab report parser. Extract ONLY the lab test values from this report.

╔══════════════════════════════════════════════════════════════╗
║  CRITICAL: YOU ARE A DATA EXTRACTOR, NOT A MEDICAL ADVISOR   ║
╚══════════════════════════════════════════════════════════════╝

YOUR ONLY JOB:
- Extract parameter names exactly as written
- Extract numeric values exactly as written
- Extract units exactly as written

YOU MUST NOT:
- Classify values as normal/high/low/abnormal
- Make any medical interpretations
- Provide ranges or recommendations
- Add any medical context

CRITICAL RULES:
1. Extract ONLY: parameter name, numeric value, and unit
2. DO NOT classify values as normal/high/low
3. DO NOT provide medical interpretations
4. DO NOT give ranges or recommendations
5. Return ONLY valid JSON - no markdown, no code blocks

Output must be a JSON object with this exact structure:
{
  "lab_values": [
    {
      "name": "parameter name",
      "value": "numeric value as string",
      "unit": "unit of measurement"
    }
  ]
}

Example output:
{
  "lab_values": [
    {"name": "Hemoglobin", "value": "11.2", "unit": "g/dL"},
    {"name": "Glucose", "value": "95", "unit": "mg/dL"},
    {"name": "Total Cholesterol", "value": "210", "unit": "mg/dL"}
  ]
}

Extract all lab parameters you find in this report. Return ONLY the JSON object.
"""

    def _parse_json_response(self, response_text: str) -> List[ExtractedLabValue]:
        """
        Parse Gemini JSON response into structured data with validation

        Args:
            response_text: JSON response from Gemini

        Returns:
            List of validated extracted lab values
        """
        try:
            clean_text = self._sanitize_json_text(response_text)

            # Parse JSON
            data = json.loads(clean_text)

            # Validate structure
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")

            if "lab_values" not in data:
                raise ValueError("Missing 'lab_values' key in response")

            lab_values = data["lab_values"]
            if not isinstance(lab_values, list):
                raise ValueError("'lab_values' must be an array")

            # Validate and parse each item
            results = []
            for idx, item in enumerate(lab_values):
                try:
                    validated_item = self._validate_lab_value(item, idx)
                    if validated_item:
                        results.append(validated_item)
                except Exception as e:
                    logger.warning(f"Skipping invalid lab value at index {idx}: {str(e)}")
                    continue

            if not results:
                raise ValueError("No valid lab values found in the report")

            logger.info(f"Successfully extracted {len(results)} lab values")
            return results

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.error(f"Response text: {response_text[:200]}...")
            raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            raise

    def _sanitize_json_text(self, response_text: str) -> str:
        """
        Clean Gemini output to isolate valid JSON.

        Handles markdown fences and leading tokens like 'json'.
        """
        clean_text = (response_text or "").strip()

        # Remove fenced markdown blocks if present.
        clean_text = re.sub(r"^```(?:json)?\\s*", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\\s*```$", "", clean_text)

        # Remove leading plain 'json' token occasionally returned by models.
        clean_text = re.sub(r"^json\\s*", "", clean_text, flags=re.IGNORECASE)

        # Keep only the outermost JSON object/array slice.
        obj_start = clean_text.find("{")
        arr_start = clean_text.find("[")
        start_candidates = [idx for idx in [obj_start, arr_start] if idx != -1]
        if start_candidates:
            start = min(start_candidates)
            last_obj = clean_text.rfind("}")
            last_arr = clean_text.rfind("]")
            end = max(last_obj, last_arr)
            if end >= start:
                clean_text = clean_text[start:end + 1]

        return clean_text.strip()

    def _validate_lab_value(self, item: Any, index: int) -> ExtractedLabValue:
        """
        Validate a single lab value item and return ExtractedLabValue

        Args:
            item: Dictionary item from JSON response
            index: Index in array (for logging)

        Returns:
            Validated ExtractedLabValue object or None if invalid
        """
        # Check if item is a dictionary
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {index} is not an object")

        # Check required fields
        required_fields = ["name", "value"]
        missing_fields = [field for field in required_fields if field not in item]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Extract and validate fields
        name = str(item["name"]).strip()
        value = str(item["value"]).strip()
        unit = str(item.get("unit", "")).strip()

        # Validate non-empty
        if not name:
            raise ValueError("Parameter name is empty")
        if not value:
            raise ValueError("Value is empty")

        # Validate value contains numeric data
        # Remove common prefixes like <, >, ~
        clean_value = value.replace("<", "").replace(">", "").replace("~", "").strip()
        try:
            float(clean_value)
        except ValueError:
            raise ValueError(f"Value '{value}' is not numeric")

        # Create validated object
        return ExtractedLabValue(
            name=name,
            value=value,
            unit=unit
        )

    def _extract_from_text_regex(self, text: str) -> List[ExtractedLabValue]:
        """
        Deterministic fallback parser for plain text reports.

        Extracts known lab parameters from lines like:
        "Hemoglobin 13.2 g/dL" or "LDL: 145 mg/dL".
        """
        if not text or not text.strip():
            return []

        parameter_patterns = {
            "Hemoglobin": r"(?:hemoglobin|\bhb\b)",
            "Glucose": r"(?:glucose|fasting\s+glucose|blood\s+glucose)",
            "Total Cholesterol": r"(?:total\s+cholesterol|\bcholesterol\b)",
            "LDL": r"(?:\bldl\b|ldl\s+cholesterol)",
            "HDL": r"(?:\bhdl\b|hdl\s+cholesterol)",
            "Triglycerides": r"triglycerides",
            "Creatinine": r"creatinine",
            "WBC": r"(?:\bwbc\b|white\s+blood\s+cells)",
            "RBC": r"(?:\brbc\b|red\s+blood\s+cells)",
            "Platelets": r"platelets",
            "TSH": r"\btsh\b",
            "ALT": r"\balt\b",
            "AST": r"\bast\b",
            "HbA1c": r"(?:hba1c|hb\s*a1c)",
            "Vitamin D": r"vitamin\s*d",
            "Vitamin B12": r"vitamin\s*b12",
        }

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        extracted: List[ExtractedLabValue] = []
        seen = set()

        for line in lines:
            for display_name, pattern in parameter_patterns.items():
                if not re.search(pattern, line, flags=re.IGNORECASE):
                    continue

                value_match = re.search(r"(?<!\d)([<>~]?\s*\d+(?:\.\d+)?)", line)
                if not value_match:
                    continue

                value = value_match.group(1).replace(" ", "")
                unit_match = re.search(r"(mg/dL|g/dL|mIU/L|U/L|ng/mL|pg/mL|%|10\^3/\w+L|10\^6/\w+L)", line, flags=re.IGNORECASE)
                unit = unit_match.group(1) if unit_match else ""

                key = (display_name.lower(), value)
                if key in seen:
                    continue

                seen.add(key)
                extracted.append(ExtractedLabValue(name=display_name, value=value, unit=unit))

        return extracted

    def _fallback_extraction(self, error_msg: str) -> List[ExtractedLabValue]:
        """
        Fallback method when extraction fails

        Args:
            error_msg: Error message from failed extraction

        Returns:
            Empty list (raises exception instead)
        """
        logger.error(f"Extraction failed, no fallback available: {error_msg}")
        raise RuntimeError(
            "Failed to extract lab values from the report. "
            "Please ensure the report contains clear lab test results with values and units. "
            f"Underlying error: {error_msg}"
        )
