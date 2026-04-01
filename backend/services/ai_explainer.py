"""
AI-powered explanation generator for lab results

╔══════════════════════════════════════════════════════════════════════╗
║  CRITICAL ARCHITECTURAL RULE: AI DOES NOT CLASSIFY                   ║
║                                                                       ║
║  This service ONLY generates explanations for ALREADY-CLASSIFIED     ║
║  lab results. The classification status (normal/high/low) is         ║
║  provided as INPUT from the rule_engine.py                           ║
║                                                                       ║
║  This service RECEIVES status (normal/high/low) from caller          ║
║  This service NEVER DETERMINES status itself                         ║
║                                                                       ║
║  Design Decision: AI is for language generation ONLY.                ║
║  Medical classification happens BEFORE this layer.                   ║
║                                                                       ║
║  PERFORMANCE OPTIMIZATION: Uses batch processing to make ONE API     ║
║  call for all explanations instead of multiple calls.                ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import os
import json
import logging
from typing import Literal, List, Dict, Any
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AIExplainer:
    """
    Generates simple explanations for lab results using AI.

    ARCHITECTURAL BOUNDARY: This class receives the classification status
    (normal/high/low) as INPUT. It does NOT and MUST NOT determine status.
    Status is determined exclusively by rule_engine.py.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)

        model_name = self._select_model_name()

        # Configure model with JSON response for batch processing
        generation_config = {
            "temperature": 0.3,  # Slightly creative for natural language
            "response_mime_type": "application/json"
        }

        self.model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config
        )
        logger.info(f"AIExplainer initialized with model: {model_name}")

    def _select_model_name(self) -> str:
        """
        Select an available Gemini model for generateContent.
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

        return "gemini-2.0-flash"

    def batch_explain_all(
        self,
        abnormal_results: List[Dict[str, Any]],
        total_count: int
    ) -> Dict[str, Any]:
        """
        Generate explanations for ALL abnormal results in ONE API call.

        ╔═══════════════════════════════════════════════════════════════╗
        ║  PERFORMANCE OPTIMIZATION: Single API Call                    ║
        ║  Instead of N calls (one per abnormal result), this makes     ║
        ║  ONE call that returns all explanations + summary + questions ║
        ╚═══════════════════════════════════════════════════════════════╝

        ARCHITECTURAL NOTE: All status values are ALREADY DETERMINED by
        rule_engine.py. The AI only generates human-readable text.

        Args:
            abnormal_results: List of dicts with keys:
                - parameter: str (e.g., "Hemoglobin")
                - value: float (e.g., 11.2)
                - unit: str (e.g., "g/dL")
                - status: Literal["high", "low"] (ALREADY CLASSIFIED)
            total_count: Total number of parameters tested

        Returns:
            Dictionary with:
                - explanations: Dict[parameter_name, explanation_text]
                - summary: Overall summary text
                - recommended_questions: List[str] of questions
        """
        if not abnormal_results:
            # No abnormal results - return simple response
            return {
                "explanations": {},
                "summary": "All your lab values are within normal ranges. This is a positive result.",
                "recommended_questions": [
                    "How often should I get these tests done?",
                    "What can I do to maintain healthy levels?",
                    "Are there any preventive measures I should take?"
                ]
            }

        try:
            prompt = self._get_batch_prompt(abnormal_results, total_count)
            logger.info(f"Making single batched API call for {len(abnormal_results)} abnormal results")

            response = self.model.generate_content(prompt)
            result = self._parse_batch_response(response.text, abnormal_results)

            logger.info("Successfully generated all explanations in one API call")
            return result

        except Exception as e:
            logger.error(f"Batch explanation failed: {str(e)}")
            # Fallback to simple explanations
            return self._get_fallback_batch_response(abnormal_results, total_count)

    def _get_batch_prompt(
        self,
        abnormal_results: List[Dict[str, Any]],
        total_count: int
    ) -> str:
        """
        Generate prompt for batch explanation generation.

        ARCHITECTURAL NOTE: All status values in abnormal_results are FACTS
        determined by rule_engine. AI must accept them, not re-classify.
        """
        abnormal_count = len(abnormal_results)

        # Build list of abnormal results for the prompt
        results_text = ""
        for i, result in enumerate(abnormal_results, 1):
            results_text += f"""
{i}. Parameter: {result['parameter']}
   Value: {result['value']} {result['unit']}
   Status: {result['status']} (ALREADY CLASSIFIED - accept as fact)
"""

        return f"""
You are explaining lab results to a patient in simple language.

╔══════════════════════════════════════════════════════════════════════╗
║  CRITICAL: All status values below were determined by medical        ║
║  reference ranges. Accept them as FACTS. Do not re-classify.         ║
╚══════════════════════════════════════════════════════════════════════╝

CONTEXT:
- Total parameters tested: {total_count}
- Abnormal parameters: {abnormal_count}
- All status classifications are FINAL (determined by reference ranges)

ABNORMAL RESULTS TO EXPLAIN:
{results_text}

YOUR TASK:
Generate explanations for each abnormal result, plus an overall summary and recommended questions.

OUTPUT FORMAT (JSON):
{{
  "explanations": {{
    "{abnormal_results[0]['parameter']}": "2-sentence explanation in simple language",
    ... (one entry for each abnormal parameter)
  }},
  "summary": "Overall summary of the report (2-3 sentences)",
  "recommended_questions": [
    "Question 1",
    "Question 2",
    "Question 3",
    "Question 4"
  ]
}}

RULES FOR EXPLANATIONS:
1. Accept status as given - never re-classify or question it
2. Use simple, non-medical language
3. Maximum 2 sentences per explanation
4. DO NOT diagnose diseases or conditions
5. DO NOT recommend medications
6. DO NOT use technical medical jargon
7. Mention what the parameter measures and what the status might indicate

RULES FOR SUMMARY:
1. State how many parameters are outside normal range
2. Use reassuring but honest tone
3. Suggest consulting doctor if multiple abnormalities
4. 2-3 sentences maximum

RULES FOR QUESTIONS:
1. Provide 4 relevant questions patients might ask
2. Questions should be practical and actionable
3. Consider whether to repeat tests, lifestyle changes, specialist consultation

Return ONLY the JSON object. No markdown, no code blocks.
"""

    def _parse_batch_response(
        self,
        response_text: str,
        abnormal_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Parse the batched JSON response from Gemini.
        """
        try:
            # Clean potential markdown
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text.split("```json")[1]
            if clean_text.startswith("```"):
                clean_text = clean_text.split("```")[1]
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("```", 1)[0]
            clean_text = clean_text.strip()

            # Parse JSON
            data = json.loads(clean_text)

            # Validate structure
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")

            required_keys = ["explanations", "summary", "recommended_questions"]
            missing_keys = [k for k in required_keys if k not in data]
            if missing_keys:
                raise ValueError(f"Missing keys in response: {missing_keys}")

            # Validate explanations dict
            if not isinstance(data["explanations"], dict):
                raise ValueError("'explanations' must be an object")

            # Validate summary
            if not isinstance(data["summary"], str) or not data["summary"].strip():
                raise ValueError("'summary' must be a non-empty string")

            # Validate questions
            if not isinstance(data["recommended_questions"], list):
                raise ValueError("'recommended_questions' must be an array")

            if len(data["recommended_questions"]) < 3:
                raise ValueError("Need at least 3 recommended questions")

            logger.info(f"Successfully parsed batch response with {len(data['explanations'])} explanations")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.error(f"Response text: {response_text[:200]}...")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            raise

    def _get_fallback_batch_response(
        self,
        abnormal_results: List[Dict[str, Any]],
        total_count: int
    ) -> Dict[str, Any]:
        """
        Fallback response if batch API call fails.
        """
        abnormal_count = len(abnormal_results)

        # Generate simple fallback explanations
        explanations = {}
        for result in abnormal_results:
            param = result['parameter']
            status = result['status']
            if status == "high":
                explanations[param] = f"Your {param} level is higher than the normal range. Consider discussing this with your doctor."
            else:  # low
                explanations[param] = f"Your {param} level is lower than the normal range. Consider discussing this with your doctor."

        # Generate fallback summary
        if abnormal_count == 1:
            summary = f"One parameter is outside the normal range among {total_count} tests. Review the details below."
        else:
            summary = f"{abnormal_count} parameters are outside normal ranges. Review each result and consider consulting your doctor."

        # Generate fallback questions
        questions = [
            "Should I repeat this test?",
            "What lifestyle changes can help improve these values?",
            "Do I need to see a specialist?",
            "Are these values concerning for my age and health status?"
        ]

        return {
            "explanations": explanations,
            "summary": summary,
            "recommended_questions": questions
        }

    def explain_result(
        self,
        parameter: str,
        value: float,
        unit: str,
        status: Literal["normal", "high", "low"]
    ) -> str:
        """
        Generate a simple explanation for a lab result.

        ARCHITECTURAL NOTE: The 'status' parameter is passed IN from the
        rule_engine.py. This method does NOT determine or change status.
        It only generates human-readable explanations for the given status.

        Args:
            parameter: Lab parameter name
            value: Numeric value
            unit: Unit of measurement
            status: Classification status (ALREADY DETERMINED by rule_engine)

        Returns:
            Simple explanation (max 2 sentences)
        """
        try:
            prompt = self._get_explanation_prompt(parameter, value, unit, status)
            response = self.model.generate_content(prompt)

            explanation = response.text.strip()

            # Ensure it's concise (max 2 sentences)
            sentences = explanation.split('.')
            if len(sentences) > 2:
                explanation = '. '.join(sentences[:2]) + '.'

            return explanation

        except Exception as e:
            logger.error(f"Failed to generate explanation: {str(e)}")
            # Fallback to generic explanation
            return self._get_fallback_explanation(parameter, status)

    def generate_summary(self, abnormal_count: int, total_count: int) -> str:
        """
        Generate overall summary of the report

        Args:
            abnormal_count: Number of abnormal results
            total_count: Total number of results

        Returns:
            Summary text
        """
        if abnormal_count == 0:
            return "All your lab values are within normal ranges. This is a positive result."
        elif abnormal_count == 1:
            return f"One parameter is outside the normal range among {total_count} tests. Review the details below."
        else:
            return f"{abnormal_count} parameters are outside normal ranges. Review each result and consider consulting your doctor."

    def generate_recommended_questions(self, has_abnormal: bool) -> list:
        """
        Generate recommended questions based on results

        Args:
            has_abnormal: Whether there are abnormal results

        Returns:
            List of recommended questions
        """
        if has_abnormal:
            return [
                "Should I repeat this test?",
                "What lifestyle changes can help improve these values?",
                "Do I need to see a specialist?",
                "Are these values concerning for my age and health status?"
            ]
        else:
            return [
                "How often should I get these tests done?",
                "What can I do to maintain healthy levels?",
                "Are there any preventive measures I should take?"
            ]

    def _get_explanation_prompt(
        self,
        parameter: str,
        value: float,
        unit: str,
        status: str
    ) -> str:
        """
        Generate prompt for explanation.

        ARCHITECTURAL NOTE: The status is passed in as FACT, not for AI to verify.
        The AI must accept the status as given and explain accordingly.

        Args:
            parameter: Lab parameter name
            value: Numeric value
            unit: Unit of measurement
            status: Classification status (ALREADY DETERMINED, not to be questioned)

        Returns:
            Prompt string
        """
        return f"""
You are explaining a lab result to a patient in simple language.

╔══════════════════════════════════════════════════════════════╗
║  IMPORTANT: The status below has been determined by medical  ║
║  reference ranges. Accept it as FACT. Do not re-classify.    ║
╚══════════════════════════════════════════════════════════════╝

Parameter: {parameter}
Value: {value} {unit}
Status: {status} (ALREADY CLASSIFIED - do not question or change this)

Provide a simple explanation (MAX 2 SENTENCES) that:
1. Explains what this parameter means in simple terms
2. If status is not "normal", briefly mention what it might indicate

RULES:
- Accept the status as given - do not re-classify
- Use simple, non-medical language
- DO NOT diagnose diseases
- DO NOT recommend medications
- DO NOT use technical jargon
- Maximum 2 sentences
- Do not suggest immediate medical action (unless critical)

Generate the explanation:
"""

    def _get_fallback_explanation(self, parameter: str, status: str) -> str:
        """
        Provide fallback explanation if AI fails

        Args:
            parameter: Lab parameter name
            status: Classification status

        Returns:
            Generic explanation
        """
        if status == "normal":
            return f"Your {parameter} level is within the normal range."
        elif status == "high":
            return f"Your {parameter} level is higher than the normal range. Consider discussing this with your doctor."
        else:  # low
            return f"Your {parameter} level is lower than the normal range. Consider discussing this with your doctor."
