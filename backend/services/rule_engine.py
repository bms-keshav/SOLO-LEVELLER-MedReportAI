"""
Rule-based validation engine for lab values

╔══════════════════════════════════════════════════════════════════════╗
║  CRITICAL ARCHITECTURAL RULE: ONLY SOURCE OF MEDICAL CLASSIFICATION  ║
║                                                                       ║
║  This is the SOLE AUTHORITY for determining:                         ║
║    ✓ "normal" status                                                 ║
║    ✓ "high" status                                                   ║
║    ✓ "low" status                                                    ║
║                                                                       ║
║  NO OTHER COMPONENT may determine these values:                      ║
║    ✗ gemini_extractor.py - extraction only, no classification       ║
║    ✗ ai_explainer.py - receives status, doesn't determine it        ║
║    ✗ No AI model anywhere - this is pure deterministic logic        ║
║                                                                       ║
║  Design Decision: Medical classification is too critical for AI.     ║
║  It must be deterministic, auditable, and explainable.               ║
║                                                                       ║
║  Algorithm: Simple comparison against reference ranges               ║
║    if value < min: return "low"                                      ║
║    if value > max: return "high"                                     ║
║    else: return "normal"                                             ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple
from utils.helpers import normalize_parameter_name, parse_numeric_value

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Rule-based engine for validating lab values against reference ranges.

    ╔═══════════════════════════════════════════════════════════════╗
    ║  THIS IS THE ONLY COMPONENT THAT PRODUCES MEDICAL STATUS     ║
    ║  ("normal", "high", "low")                                    ║
    ║                                                               ║
    ║  NO AI - Pure deterministic logic based on reference ranges  ║
    ╚═══════════════════════════════════════════════════════════════╝

    This is NOT AI-based. It uses pure rule matching against reference
    ranges loaded from a JSON file. Every decision is deterministic,
    auditable, and explainable.
    """

    def __init__(self, reference_file: str = "data/reference_ranges.json"):
        self.reference_ranges = self._load_reference_ranges(reference_file)

    def _load_reference_ranges(self, file_path: str) -> Dict:
        """
        Load reference ranges from JSON file

        Args:
            file_path: Path to reference ranges file

        Returns:
            Dictionary of reference ranges
        """
        try:
            full_path = Path(__file__).parent.parent / file_path
            with open(full_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load reference ranges: {str(e)}")
            raise RuntimeError(f"Could not load reference ranges: {str(e)}")

    def _safe_to_float(self, raw_value, context: str = "") -> Optional[float]:
        """
        Safely convert values to float, handling symbols like '< 200' or '>50'.
        """
        try:
            if raw_value is None:
                return None

            if isinstance(raw_value, (int, float)):
                return float(raw_value)

            text = str(raw_value).strip()
            if not text:
                return None

            # Keep the first numeric token after stripping comparison symbols.
            text = re.sub(r"^[<>~=]+", "", text).strip()
            match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
            if not match:
                return None

            return float(match.group(0))
        except Exception as e:
            logger.error(f"Safe float conversion failed ({context}): {e}")
            print(f"Error in rule engine: {e}")
            return None

    def _resolve_parameter_key(self, parameter: str) -> Optional[str]:
        """
        Resolve input parameter to a reference key using exact matching and aliases.
        Example: 'Hemoglobin (Hb)' -> 'hemoglobin' or 'hb'.
        """
        try:
            if not parameter or not isinstance(parameter, str):
                return None

            candidate_keys = []

            # 1) Exact normalized input
            normalized_name = normalize_parameter_name(parameter)
            candidate_keys.append(normalized_name)

            # 2) Exact normalized name after removing parenthetical content.
            no_parens = re.sub(r"\([^)]*\)", "", parameter)
            normalized_no_parens = normalize_parameter_name(no_parens)
            candidate_keys.append(normalized_no_parens)

            # 3) Aliases inside parentheses, e.g., (Hb)
            paren_parts = re.findall(r"\(([^)]*)\)", parameter)
            for part in paren_parts:
                alias = normalize_parameter_name(part)
                candidate_keys.append(alias)

            # 4) De-duplicated exact checks only (no containment-based fuzzy matching).
            seen = set()
            for key in candidate_keys:
                if not key or key in seen:
                    continue
                seen.add(key)
                if key in self.reference_ranges:
                    return key

            return None
        except Exception as e:
            logger.error(f"Parameter key resolution failed for '{parameter}': {e}")
            print(f"Error in rule engine: {e}")
            return None

    def validate_value(
        self,
        parameter: str,
        value: str
    ) -> Tuple[Literal["normal", "high", "low", "unknown"], Optional[Dict]]:
        """
        Validate a lab value against reference ranges.

        ╔═══════════════════════════════════════════════════════════════╗
        ║  SOLE SOURCE OF MEDICAL STATUS - NO AI INVOLVED              ║
        ╚═══════════════════════════════════════════════════════════════╝

        This method is the ONLY place in the entire system where medical
        status (normal/high/low) is determined. It uses simple, deterministic
        logic: compare numeric value against min/max reference ranges.

        NO AI model is consulted. NO probabilistic decisions. Only math.

        Args:
            parameter: Parameter name (e.g., "Hemoglobin")
            value: Value as string (e.g., "11.2")

        Returns:
            Tuple of (status, reference_info)
            status: "normal", "high", "low", or "unknown"
            reference_info: Dict with min, max, unit, display_name or None
        """
        try:
            # ═══════════════════════════════════════════════════════════
            # INPUT VALIDATION
            # ═══════════════════════════════════════════════════════════
            # Validate parameter name
            if not parameter or not isinstance(parameter, str):
                logger.warning(f"Invalid parameter name: {parameter}")
                return "unknown", None

            # Validate value
            if value is None:
                logger.warning(f"Value is None for parameter: {parameter}")
                return "unknown", None

            # Normalize/fuzzy-resolve parameter key for lookup.
            normalized_name = self._resolve_parameter_key(parameter)

            # Check if we have a reference range for this parameter
            if not normalized_name or normalized_name not in self.reference_ranges:
                logger.debug(f"No reference range found for: {parameter} (normalized: {normalized_name})")
                return "unknown", None

            # Parse numeric value
            numeric_value = parse_numeric_value(value)
            if numeric_value is None:
                numeric_value = self._safe_to_float(value, context=f"value:{parameter}")
            if numeric_value is None:
                logger.warning(f"Could not parse value '{value}' for parameter: {parameter}")
                return "unknown", None

            # ═══════════════════════════════════════════════════════════
            # REFERENCE RANGE VALIDATION
            # ═══════════════════════════════════════════════════════════
            # Get reference range
            ref = self.reference_ranges[normalized_name]

            # Validate reference structure
            if not isinstance(ref, dict):
                logger.error(f"Invalid reference structure for {parameter}: not a dict")
                return "unknown", None

            required_keys = ["min", "max", "unit", "display_name"]
            missing_keys = [k for k in required_keys if k not in ref]
            if missing_keys:
                logger.error(f"Missing keys in reference for {parameter}: {missing_keys}")
                return "unknown", None

            # Validate min/max values
            try:
                min_val = self._safe_to_float(ref["min"], context=f"min:{parameter}")
                max_val = self._safe_to_float(ref["max"], context=f"max:{parameter}")
                if min_val is None or max_val is None:
                    raise ValueError("Reference min/max could not be converted to float")
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid min/max values for {parameter}: {e}")
                print(f"Error in rule engine: {e}")
                return "unknown", None

            # Sanity check on reference range
            if min_val < 0 or max_val < 0:
                logger.warning(f"Negative reference range for {parameter}: min={min_val}, max={max_val}")

            if min_val > max_val:
                logger.error(f"Invalid reference range for {parameter}: min ({min_val}) > max ({max_val})")
                return "unknown", None

            # ═══════════════════════════════════════════════════════════
            # CLASSIFICATION: RULE-BASED LOGIC (NO AI)
            # ═══════════════════════════════════════════════════════════
            # Simple mathematical comparison
            if numeric_value < min_val:
                status = "low"
            elif numeric_value > max_val:
                status = "high"
            else:
                status = "normal"

            # Return status and reference info
            return status, ref

        except KeyError as e:
            logger.error(f"KeyError validating {parameter}: {str(e)}")
            print(f"Error in rule engine: {e}")
            return "unknown", None
        except Exception as e:
            logger.error(f"Unexpected error validating {parameter}: {str(e)}")
            print(f"Error in rule engine: {e}")
            return "unknown", None

    def get_reference_range(self, parameter: str) -> Optional[Dict]:
        """
        Get reference range for a parameter

        Args:
            parameter: Parameter name

        Returns:
            Reference info or None if not found
        """
        normalized_name = normalize_parameter_name(parameter)
        return self.reference_ranges.get(normalized_name)

    def get_all_parameters(self) -> list:
        """
        Get list of all supported parameters

        Returns:
            List of parameter names
        """
        return list(self.reference_ranges.keys())
