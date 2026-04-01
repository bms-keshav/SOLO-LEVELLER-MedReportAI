"""
Pydantic models for request/response validation
"""
from typing import List, Literal
from pydantic import BaseModel, Field


class ExtractedLabValue(BaseModel):
    """Raw lab value extracted from report"""
    name: str = Field(..., description="Parameter name (e.g., Hemoglobin)")
    value: str = Field(..., description="Numeric value as string")
    unit: str = Field(..., description="Unit of measurement (e.g., g/dL)")


class AnalyzedResult(BaseModel):
    """Analyzed lab result with classification and explanation"""
    parameter: str = Field(..., description="Lab parameter name")
    value: float = Field(..., description="Numeric value")
    unit: str = Field(..., description="Unit of measurement")
    status: Literal["normal", "high", "low"] = Field(..., description="Classification status")
    explanation: str = Field(..., description="Simple explanation of the result")
    reference_range: str = Field(..., description="Normal reference range")


class AnalysisResponse(BaseModel):
    """Complete analysis response"""
    summary: str = Field(..., description="Overall summary of the report")
    urgency_level: Literal["Normal", "Monitor", "Consult Doctor"] = Field(
        ..., description="Urgency classification"
    )
    results: List[AnalyzedResult] = Field(..., description="Individual lab results")
    recommended_questions: List[str] = Field(
        ..., description="Suggested questions for the patient"
    )


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="ok")


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_type: str
