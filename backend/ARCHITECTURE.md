# MedReport AI - System Architecture

## Overview

MedReport AI is a production-quality medical lab report analysis system that converts complex lab reports into simple, understandable insights for patients.

## Design Principles

### 1. **Separation of Concerns**
- **Extraction** (AI) → **Validation** (Rules) → **Explanation** (AI)
- Each layer has a single, well-defined responsibility
- No layer performs tasks outside its domain

### 2. **AI Limitations by Design**
- AI is NOT used for medical classification
- AI ONLY used where appropriate: OCR/extraction and language generation
- Critical medical logic uses deterministic, rule-based systems

### 3. **Modularity**
- Each service is independently testable
- Easy to swap implementations (e.g., switch from Gemini to GPT)
- Clear interfaces between components

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Server                        │
│                         (main.py)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Routes Layer                         │
│                    (routes/analyze.py)                       │
│  • File validation                                           │
│  • Orchestrates the 3-step pipeline                          │
│  • Error handling & response formatting                      │
└────┬──────────────────┬──────────────────┬──────────────────┘
     │                  │                  │
     │ STEP 1           │ STEP 2           │ STEP 3
     │ Extract          │ Validate         │ Explain
     │                  │                  │
     ▼                  ▼                  ▼
┌────────────┐   ┌─────────────┐   ┌──────────────┐
│  Gemini    │   │    Rule     │   │     AI       │
│ Extractor  │   │   Engine    │   │  Explainer   │
│            │   │             │   │              │
│ • PDF OCR  │   │ • Load refs │   │ • Generate   │
│ • Image    │   │ • Compare   │   │   summaries  │
│   analysis │   │   values    │   │ • Create     │
│ • Struct.  │   │ • Classify  │   │   questions  │
│   output   │   │   status    │   │              │
└────────────┘   └─────┬───────┘   └──────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Reference     │
              │  Ranges        │
              │  (JSON)        │
              └────────────────┘
```

## Component Details

### 1. File Processing Layer (`utils/helpers.py`)
**Purpose:** Handle file I/O and data formatting

**Functions:**
- `extract_text_from_pdf()` - PDF text extraction
- `validate_image()` - Image validation
- `normalize_parameter_name()` - Standardize parameter names
- `parse_numeric_value()` - Extract numbers from strings
- `format_reference_range()` - Display-friendly formatting

**Why separate?**
- Keeps business logic clean
- Easy to add new file formats
- Reusable across services

### 2. Gemini Extractor (`services/gemini_extractor.py`)
**Purpose:** Extract structured lab values ONLY

**Key Design Decisions:**
- ✅ Extracts: parameter name, value, unit
- ❌ Does NOT: classify, interpret, or recommend
- Uses strict prompt engineering to prevent overreach
- Returns structured `ExtractedLabValue` objects

**Prompt Strategy:**
```
CRITICAL RULES:
1. Extract ONLY: parameter name, numeric value, and unit
2. DO NOT classify values as normal/high/low
3. DO NOT provide medical interpretations
```

**Why this approach?**
- AI is excellent at parsing unstructured data
- AI should NOT make medical decisions
- Keeps AI role clearly bounded

### 3. Rule Engine (`services/rule_engine.py`)
**Purpose:** Deterministic classification of lab values

**Key Design Decisions:**
- Pure Python logic - NO AI
- Loads reference ranges from JSON
- Simple comparison: `value < min → low`, `value > max → high`
- Returns status + reference data

**Why rule-based?**
- Medical classification must be deterministic
- Auditable and explainable
- No hallucination risk
- Easy to update reference ranges

**Reference Data Structure:**
```json
{
  "hemoglobin": {
    "min": 12.0,
    "max": 16.0,
    "unit": "g/dL",
    "display_name": "Hemoglobin"
  }
}
```

### 4. AI Explainer (`services/ai_explainer.py`)
**Purpose:** Generate patient-friendly explanations

**Key Design Decisions:**
- ✅ Explains: what parameter means, what abnormal might indicate
- ❌ Does NOT: diagnose, prescribe, or give medical advice
- Max 2 sentences per explanation
- Fallback explanations if AI fails

**Prompt Strategy:**
```
RULES:
- Use simple, non-medical language
- DO NOT diagnose diseases
- DO NOT recommend medications
- Maximum 2 sentences
```

**Why use AI here?**
- Language generation is AI's strength
- Explanations are non-critical (have fallbacks)
- Makes technical terms accessible

### 5. Data Models (`models/schemas.py`)
**Purpose:** Type-safe data contracts

**Models:**
- `ExtractedLabValue` - Raw extraction output
- `AnalyzedResult` - Complete analysis result
- `AnalysisResponse` - Final API response
- `HealthResponse` - Health check
- `ErrorResponse` - Error handling

**Why Pydantic?**
- Automatic validation
- Clear API contracts
- Self-documenting
- Type safety

## Data Flow

### Complete Request Flow

```
1. File Upload (PDF/Image)
   ↓
2. File Validation (type, format)
   ↓
3. EXTRACTION PHASE: Gemini API
   - Input: File bytes
   - Output: [{"name": "Hemoglobin", "value": "11.2", "unit": "g/dL"}]
   ↓
4. VALIDATION PHASE: Rule Engine
   - Input: Extracted values
   - Process: Load refs → Compare → Classify
   - Output: status (normal/high/low) + reference data
   ↓
5. EXPLANATION PHASE: AI Explainer
   - Input: Parameter + Status
   - Process: Generate simple explanation (if abnormal)
   - Output: Patient-friendly text
   ↓
6. AGGREGATION: Build Response
   - Count abnormal results
   - Determine urgency level
   - Generate summary
   - Create recommended questions
   ↓
7. Return JSON Response
```

## Error Handling Strategy

### Layered Error Handling

1. **Input Validation**
   - Invalid file type → 400 Bad Request
   - Corrupted file → 400 Bad Request

2. **Processing Errors**
   - Gemini API failure → 500 Server Error (with retry logic)
   - No values extracted → 422 Unprocessable Entity
   - Parse failures → Warning + skip parameter

3. **Graceful Degradation**
   - AI explanation fails → Use fallback text
   - Unknown parameter → Skip but process others
   - Partial results → Return what's available

### Logging
- INFO: Normal flow milestones
- WARNING: Recoverable issues
- ERROR: Failures requiring attention

## Security Considerations

1. **API Key Management**
   - Environment variables only
   - Never hardcoded
   - .env excluded from git

2. **File Upload Safety**
   - Type validation
   - Size limits (implicit)
   - Content validation

3. **Data Privacy**
   - No data persistence (stateless)
   - No patient data logged
   - CORS configurable

## Performance Optimization

1. **Async Operations**
   - FastAPI async endpoints
   - Non-blocking I/O

2. **Minimal Dependencies**
   - Only essential packages
   - Fast startup time

3. **Efficient Processing**
   - Single-pass analysis
   - Early validation failures
   - Parallel-ready design

## Extensibility Points

### Easy to Add:

1. **New Lab Parameters**
   - Edit `reference_ranges.json`
   - No code changes needed

2. **New File Formats**
   - Add parser in `utils/helpers.py`
   - Update `determine_file_type()`

3. **Alternative AI Providers**
   - Implement interface in new service
   - Swap in `routes/analyze.py`

4. **Additional Validations**
   - Add methods to `RuleEngine`
   - Hook into validation phase

## Testing Strategy

### Unit Tests (Recommended)
```python
# Test rule engine
def test_rule_engine_classification():
    engine = RuleEngine()
    status, ref = engine.validate_value("Hemoglobin", "11.2")
    assert status == "low"

# Test helpers
def test_normalize_parameter_name():
    assert normalize_parameter_name("Hb") == "hb"
    assert normalize_parameter_name("Blood Glucose") == "blood_glucose"
```

### Integration Tests
```python
# Test complete flow
def test_analyze_report_endpoint():
    with open("sample_report.pdf", "rb") as f:
        response = client.post("/api/analyze-report", files={"file": f})
    assert response.status_code == 200
    assert "results" in response.json()
```

## Production Checklist

- [ ] Set production GEMINI_API_KEY
- [ ] Configure CORS for production domain
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Set up monitoring (e.g., Sentry)
- [ ] Add request logging
- [ ] Implement caching (if needed)
- [ ] Add authentication (if required)
- [ ] Set up CI/CD pipeline
- [ ] Load test endpoints

## Technology Choices

### Why FastAPI?
- Modern, fast, async-native
- Automatic API docs
- Type hints + validation
- Production-ready

### Why Gemini?
- Excellent vision capabilities (OCR)
- Good structured output
- Cost-effective
- Easy to use

### Why Rule-Based Validation?
- Medical decisions need determinism
- Explainable to regulators
- No AI unpredictability
- Easy to audit

## Future Enhancements

### Potential Additions:
1. **Multi-language support** - Translate explanations
2. **Historical tracking** - Compare with previous reports
3. **PDF report generation** - Export analysis
4. **Batch processing** - Handle multiple files
5. **Admin dashboard** - Monitor usage
6. **Custom ranges** - Per-user reference ranges
7. **ML trend analysis** - Detect patterns over time

---

## Summary

This architecture achieves:
- ✅ Clear separation of concerns
- ✅ AI used only where appropriate
- ✅ Deterministic medical logic
- ✅ Production-ready code quality
- ✅ Easy to extend and maintain
- ✅ Secure and performant

**Key Insight:** AI is a tool in our pipeline, not the decision-maker. Critical medical logic stays in deterministic, auditable code.
