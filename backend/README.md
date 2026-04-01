# MedReport AI - Backend

Production-quality FastAPI backend for medical lab report analysis.

## Architecture

This system follows a strict separation of concerns:

1. **Gemini API** - ONLY for extracting structured lab values (name, value, unit)
2. **Rule Engine** - Pure Python logic for classification (normal/high/low)
3. **AI Explainer** - Gemini for generating patient-friendly explanations

## Project Structure

```
backend/
├── main.py                  # FastAPI app entry point
├── routes/
│   └── analyze.py          # API endpoints
├── services/
│   ├── gemini_extractor.py # Gemini extraction service
│   ├── rule_engine.py      # Rule-based validation
│   └── ai_explainer.py     # AI explanation generator
├── models/
│   └── schemas.py          # Pydantic models
├── data/
│   └── reference_ranges.json # Lab value reference ranges
├── utils/
│   └── helpers.py          # Utility functions
└── requirements.txt        # Dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```
GEMINI_API_KEY=your_gemini_api_key_here
ALLOWED_ORIGINS=http://localhost:3000
# MAX_FILE_SIZE_BYTES=10485760
# GEMINI_MODEL=gemini-2.0-flash
```

Get your Gemini API key from: https://ai.google.dev/

### 3. Run the Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server will start at: `http://localhost:8000`

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

### Analyze Report

```
POST /api/analyze-report
```

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (PDF, JPG, or PNG)

**Response:**
```json
{
  "summary": "All your lab values are within normal ranges.",
  "urgency_level": "Normal",
  "results": [
    {
      "parameter": "Hemoglobin",
      "value": 14.5,
      "unit": "g/dL",
      "status": "normal",
      "explanation": "Your Hemoglobin level is within the normal range.",
      "reference_range": "12.0 - 16.0 g/dL"
    }
  ],
  "recommended_questions": [
    "How often should I get these tests done?",
    "What can I do to maintain healthy levels?"
  ]
}
```

## Processing Flow

1. **File Upload** → Validate file type (PDF/image)
2. **Extraction** → Use Gemini to extract structured values
3. **Validation** → Apply rule-based classification (no AI)
4. **Explanation** → Generate simple explanations using AI
5. **Response** → Return structured JSON

## Supported Lab Parameters

The system currently supports these parameters (configurable in `data/reference_ranges.json`):

- Hemoglobin (Hb)
- Glucose (Fasting)
- Cholesterol (Total, LDL, HDL)
- Triglycerides
- Creatinine
- White Blood Cells (WBC)
- Red Blood Cells (RBC)
- Platelets
- TSH (Thyroid)
- Liver enzymes (ALT, AST)
- HbA1c
- Vitamins (D, B12)

## Adding New Parameters

Edit `data/reference_ranges.json`:

```json
{
  "parameter_name": {
    "min": 0.0,
    "max": 100.0,
    "unit": "mg/dL",
    "display_name": "Parameter Display Name"
  }
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200` - Success
- `400` - Invalid file type or format
- `413` - Uploaded file exceeds max allowed size
- `422` - Processing error (no values found)
- `500` - Server error

## Logging

Logs are written to stdout with timestamps and log levels:

```
2025-01-15 10:30:45 - main - INFO - Starting MedReport AI backend...
2025-01-15 10:30:46 - analyze - INFO - Processing file: report.pdf (type: pdf)
```

## Security Notes

- Always use environment variables for API keys
- Configure CORS appropriately for production
- Validate all file uploads
- Implement rate limiting for production use

## Testing

Run automated tests:

```bash
pytest -q
```

Quick API test with curl:

```bash
curl -X POST http://localhost:8000/api/analyze-report \
  -F "file=@sample_report.pdf"
```

## Production Deployment

For production:

1. Set proper CORS origins
2. Use a production ASGI server (Gunicorn + Uvicorn)
3. Enable HTTPS
4. Implement rate limiting
5. Add authentication if needed
6. Monitor API usage and costs

## License

MIT
