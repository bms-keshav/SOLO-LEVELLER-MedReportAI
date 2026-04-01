"""
API routes for report analysis

╔══════════════════════════════════════════════════════════════════════╗
║  ARCHITECTURAL OVERVIEW: 3-STEP PIPELINE WITH STRICT SEPARATION     ║
║                                                                       ║
║  STEP 1: EXTRACTION (AI)                                             ║
║    Service: gemini_extractor.py                                      ║
║    Output: {name, value, unit}                                       ║
║    Does NOT classify as normal/high/low                              ║
║                                                                       ║
║  STEP 2: CLASSIFICATION (RULES - NO AI)                              ║
║    Service: rule_engine.py                                           ║
║    Output: status (normal/high/low)                                  ║
║    THIS IS THE ONLY PLACE status is determined                       ║
║                                                                       ║
║  STEP 3: EXPLANATION (AI)                                            ║
║    Service: ai_explainer.py                                          ║
║    Input: ALREADY CLASSIFIED status from Step 2                      ║
║    Output: Patient-friendly explanation text                         ║
║    Does NOT re-classify or change status                             ║
║                                                                       ║
║  Design Decision: Medical classification too critical for AI.        ║
║  AI is used for parsing (Step 1) and language (Step 3) only.        ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from models.schemas import AnalysisResponse, AnalyzedResult
from services.gemini_extractor import GeminiExtractor
from services.rule_engine import RuleEngine
from services.ai_explainer import AIExplainer
from utils.helpers import (
    determine_file_type,
    extract_text_from_pdf,
    validate_image,
    parse_numeric_value,
    format_reference_range
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services lazily so the API can still boot and expose /health
# even when Gemini configuration is missing or temporarily invalid.
gemini_extractor = None
rule_engine = None
ai_explainer = None


def get_gemini_extractor() -> GeminiExtractor:
    global gemini_extractor
    if gemini_extractor is None:
        gemini_extractor = GeminiExtractor()  # AI for extraction only
    return gemini_extractor


def get_rule_engine() -> RuleEngine:
    global rule_engine
    if rule_engine is None:
        rule_engine = RuleEngine()  # NO AI - deterministic classification
    return rule_engine


def get_ai_explainer() -> AIExplainer:
    global ai_explainer
    if ai_explainer is None:
        ai_explainer = AIExplainer()  # AI for explanations only
    return ai_explainer


@router.post("/analyze-report", response_model=AnalysisResponse)
async def analyze_report(file: UploadFile = File(...)):
    """
    Analyze a medical lab report (PDF or image)

    ╔═══════════════════════════════════════════════════════════════╗
    ║  3-STEP PROCESSING PIPELINE                                   ║
    ║                                                               ║
    ║  1. AI Extraction    → {name, value, unit}                   ║
    ║  2. Rule Validation  → status (normal/high/low)              ║
    ║  3. AI Explanation   → human-readable text                   ║
    ╚═══════════════════════════════════════════════════════════════╝

    Args:
        file: Uploaded file (PDF, JPG, PNG)

    Returns:
        AnalysisResponse with structured results and explanations
    """
    try:
        extractor = get_gemini_extractor()
        rules = get_rule_engine()
        explainer = get_ai_explainer()

        # Read file content
        file_content = await file.read()
        file_type = determine_file_type(file.filename)

        logger.info(f"Processing file: {file.filename} (type: {file_type})")

        # Validate file type
        if file_type == 'unknown':
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload PDF, JPG, or PNG files."
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: EXTRACT LAB VALUES (AI - EXTRACTION ONLY)
        # ═══════════════════════════════════════════════════════════════
        # Gemini API extracts: {name, value, unit}
        # Does NOT classify as normal/high/low
        # ═══════════════════════════════════════════════════════════════
        logger.info("Step 1: Extracting lab values using Gemini API (extraction only, no classification)...")

        if file_type == 'pdf':
            text = extract_text_from_pdf(file_content)

            # Prefer text extraction for digital PDFs, but fall back to direct
            # PDF multimodal extraction for scanned/image-based reports.
            if text and len(text.strip()) >= 30:
                try:
                    extracted_values = extractor.extract_from_text(text)
                except Exception as text_error:
                    logger.warning(
                        f"Text-based PDF extraction failed ({text_error}); trying direct PDF extraction"
                    )
                    extracted_values = extractor.extract_from_pdf(file_content)
            else:
                logger.info("PDF appears scanned or has minimal text; using direct PDF extraction")
                extracted_values = extractor.extract_from_pdf(file_content)
        else:  # image
            if not validate_image(file_content):
                raise HTTPException(status_code=400, detail="Invalid image file")
            extracted_values = extractor.extract_from_image(file_content)

        logger.info(f"Extracted {len(extracted_values)} lab values (raw data only, not classified)")

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: VALIDATE USING RULE ENGINE (NO AI - DETERMINISTIC)
        # ═══════════════════════════════════════════════════════════════
        # Rule engine DETERMINES medical status: normal/high/low
        # This is the ONLY place where status is assigned
        # Pure comparison logic: value < min → low, value > max → high
        # ═══════════════════════════════════════════════════════════════
        logger.info("Step 2: Classifying values using rule-based engine (SOLE SOURCE of medical status)...")

        # Collect all results (normal and abnormal) without AI explanations yet
        classified_results = []
        abnormal_results_for_ai = []  # Will be sent to AI in ONE batch call
        validation_errors = []  # Track validation issues

        for idx, lab_value in enumerate(extracted_values):
            # ═══════════════════════════════════════════════════════════
            # PRE-VALIDATION: Ensure safe input before rule engine
            # ═══════════════════════════════════════════════════════════
            # Validate required fields exist
            try:
                if not hasattr(lab_value, 'name') or not lab_value.name:
                    validation_errors.append(f"Entry {idx}: Missing or empty 'name' field")
                    logger.warning(f"Skipping entry {idx}: Missing or empty 'name' field")
                    continue

                if not hasattr(lab_value, 'value') or not lab_value.value:
                    validation_errors.append(f"Entry {idx} ({lab_value.name}): Missing or empty 'value' field")
                    logger.warning(f"Skipping {lab_value.name}: Missing or empty 'value' field")
                    continue

                # Safe conversion to float
                numeric_value = parse_numeric_value(lab_value.value)
                if numeric_value is None:
                    validation_errors.append(f"{lab_value.name}: Could not parse value '{lab_value.value}' as number")
                    logger.warning(f"Skipping {lab_value.name}: Invalid numeric value '{lab_value.value}'")
                    continue

                # Validate numeric value is reasonable
                if numeric_value < 0:
                    validation_errors.append(f"{lab_value.name}: Negative value {numeric_value} not allowed")
                    logger.warning(f"Skipping {lab_value.name}: Negative value {numeric_value}")
                    continue

                if numeric_value > 1e6:  # Unreasonably large
                    validation_errors.append(f"{lab_value.name}: Value {numeric_value} exceeds reasonable range")
                    logger.warning(f"Skipping {lab_value.name}: Unreasonably large value {numeric_value}")
                    continue

                # Validate value is not NaN or infinity
                if not (numeric_value == numeric_value):  # NaN check
                    validation_errors.append(f"{lab_value.name}: Value is NaN")
                    logger.warning(f"Skipping {lab_value.name}: Value is NaN")
                    continue

                if numeric_value == float('inf') or numeric_value == float('-inf'):
                    validation_errors.append(f"{lab_value.name}: Value is infinity")
                    logger.warning(f"Skipping {lab_value.name}: Value is infinity")
                    continue

            except AttributeError as e:
                validation_errors.append(f"Entry {idx}: Missing required attribute - {str(e)}")
                logger.error(f"Skipping entry {idx}: AttributeError - {str(e)}")
                continue
            except Exception as e:
                validation_errors.append(f"Entry {idx}: Validation error - {str(e)}")
                logger.error(f"Skipping entry {idx}: Unexpected validation error - {str(e)}")
                continue

            # ═══════════════════════════════════════════════════════════
            # CLASSIFICATION HAPPENS HERE (rule_engine.validate_value)
            # This is the ONLY place that produces "normal"/"high"/"low"
            # NO AI involved - pure mathematical comparison
            # ═══════════════════════════════════════════════════════════
            try:
                status, ref_info = rules.validate_value(
                    lab_value.name,
                    lab_value.value
                )
            except Exception as e:
                validation_errors.append(f"{lab_value.name}: Rule engine error - {str(e)}")
                logger.error(f"Skipping {lab_value.name}: Rule engine error - {str(e)}")
                continue

            # Skip if we don't have reference data
            if status == "unknown" or ref_info is None:
                logger.info(f"Info: {lab_value.name} - no reference range available (not an error)")
                continue

            # ═══════════════════════════════════════════════════════════
            # SAFE RESULT CONSTRUCTION
            # ═══════════════════════════════════════════════════════════
            try:
                # Validate ref_info structure
                if not isinstance(ref_info, dict):
                    validation_errors.append(f"{lab_value.name}: Invalid reference info structure")
                    logger.error(f"Skipping {lab_value.name}: ref_info is not a dict")
                    continue

                required_ref_keys = ["display_name", "min", "max", "unit"]
                missing_ref_keys = [k for k in required_ref_keys if k not in ref_info]
                if missing_ref_keys:
                    validation_errors.append(f"{lab_value.name}: Missing reference keys: {missing_ref_keys}")
                    logger.error(f"Skipping {lab_value.name}: Missing reference keys: {missing_ref_keys}")
                    continue

                # Format reference range safely
                ref_range = format_reference_range(
                    ref_info["min"],
                    ref_info["max"],
                    ref_info["unit"]
                )

                # Store classified result (explanation will be added later)
                result_unit = ""
                if hasattr(lab_value, 'unit') and isinstance(lab_value.unit, str):
                    result_unit = lab_value.unit.strip()
                if not result_unit:
                    result_unit = str(ref_info["unit"])

                result_data = {
                    "parameter": ref_info["display_name"],
                    "value": numeric_value,
                    "unit": result_unit,
                    "status": status,
                    "reference_range": ref_range,
                    "explanation": None  # Will be filled by AI in batch
                }

                classified_results.append(result_data)

                # If abnormal, add to batch for AI explanation
                if status != "normal":
                    abnormal_results_for_ai.append({
                        "parameter": ref_info["display_name"],
                        "value": numeric_value,
                        "unit": result_unit,
                        "status": status  # ← Status from rule_engine, NOT from AI
                    })

                logger.debug(f"✓ Successfully validated and classified: {lab_value.name} = {numeric_value} {result_unit} ({status})")

            except KeyError as e:
                validation_errors.append(f"{lab_value.name}: Missing key in reference data - {str(e)}")
                logger.error(f"Skipping {lab_value.name}: Missing key in reference data - {str(e)}")
                continue
            except Exception as e:
                validation_errors.append(f"{lab_value.name}: Error constructing result - {str(e)}")
                logger.error(f"Skipping {lab_value.name}: Error constructing result - {str(e)}")
                continue

        # ═══════════════════════════════════════════════════════════════
        # POST-VALIDATION SUMMARY
        # ═══════════════════════════════════════════════════════════════
        total_extracted = len(extracted_values)
        total_classified = len(classified_results)
        total_skipped = total_extracted - total_classified

        logger.info(f"Validation summary: {total_classified}/{total_extracted} successfully classified, {total_skipped} skipped")

        if validation_errors:
            logger.warning(f"Validation issues encountered: {len(validation_errors)} entries had problems")
            for error in validation_errors[:10]:  # Log first 10 errors
                logger.warning(f"  - {error}")
            if len(validation_errors) > 10:
                logger.warning(f"  ... and {len(validation_errors) - 10} more")

        if not classified_results:
            # Enhanced error message with validation details
            error_detail = "Could not analyze any values from the report. "
            if validation_errors:
                error_detail += f"Encountered {len(validation_errors)} validation issues. "
            error_detail += "Please ensure the report contains standard lab test results with valid numeric values."

            raise HTTPException(
                status_code=422,
                detail=error_detail
            )

        logger.info(f"Classified {len(classified_results)} results: {len(abnormal_results_for_ai)} abnormal, {len(classified_results) - len(abnormal_results_for_ai)} normal")

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: GENERATE ALL EXPLANATIONS IN ONE BATCHED API CALL
        # ═══════════════════════════════════════════════════════════════
        # OPTIMIZATION: Instead of N API calls (one per abnormal result),
        # make ONE call that returns all explanations + summary + questions
        # ═══════════════════════════════════════════════════════════════
        # ARCHITECTURAL NOTE: AI receives ALREADY-DETERMINED status values
        # AI does NOT re-classify - only generates patient-friendly text
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"Step 3: Generating explanations in ONE batched API call for {len(abnormal_results_for_ai)} abnormal results...")

        # Make single batched API call
        ai_response = explainer.batch_explain_all(
            abnormal_results=abnormal_results_for_ai,
            total_count=len(classified_results)
        )

        # Extract components from AI response
        explanations_map = ai_response["explanations"]
        summary = ai_response["summary"]
        recommended_questions = ai_response["recommended_questions"]

        logger.info(f"✓ Received {len(explanations_map)} explanations in single API call (vs {len(abnormal_results_for_ai)} separate calls)")

        # ═══════════════════════════════════════════════════════════════
        # MAP EXPLANATIONS BACK TO RESULTS
        # ═══════════════════════════════════════════════════════════════
        analyzed_results = []
        for result_data in classified_results:
            param = result_data["parameter"]

            # Get explanation from AI response or use default for normal
            if result_data["status"] == "normal":
                explanation = f"Your {param} level is within the normal range."
            else:
                # Get explanation from batched AI response
                explanation = explanations_map.get(
                    param,
                    f"Your {param} level is {result_data['status']}. Consider discussing this with your doctor."
                )

            # Create final AnalyzedResult
            analyzed_results.append(AnalyzedResult(
                parameter=result_data["parameter"],
                value=result_data["value"],
                unit=result_data["unit"],
                status=result_data["status"],
                explanation=explanation,
                reference_range=result_data["reference_range"]
            ))

        # ═══════════════════════════════════════════════════════════════
        # STEP 4: DETERMINE URGENCY (RULE-BASED - NO AI)
        # ═══════════════════════════════════════════════════════════════
        # Simple deterministic rules based on abnormal count
        # NO AI involved in this critical decision
        # ═══════════════════════════════════════════════════════════════
        abnormal_count = len(abnormal_results_for_ai)

        if abnormal_count == 0:
            urgency_level = "Normal"
        elif abnormal_count <= 2:
            urgency_level = "Monitor"
        else:
            urgency_level = "Consult Doctor"

        logger.info(f"Urgency level determined by rules: {urgency_level} (abnormal count: {abnormal_count})")
        logger.info(f"Performance: Made 1 AI call instead of {len(abnormal_results_for_ai) + 2} calls")

        # Build final response
        response = AnalysisResponse(
            summary=summary,  # From batched AI call
            urgency_level=urgency_level,  # From rule-based logic
            results=analyzed_results,
            recommended_questions=recommended_questions  # From batched AI call
        )

        logger.info(f"Analysis complete: {len(analyzed_results)} results, {abnormal_count} abnormal")

        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
