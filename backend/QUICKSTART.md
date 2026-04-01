# 🚀 Quick Start Guide

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Gemini API key from [Google AI Studio](https://ai.google.dev/)

## Installation Steps

### Option 1: Automated Setup (Recommended)

**On Linux/Mac:**
```bash
cd backend
chmod +x start.sh
./start.sh
```

**On Windows:**
```bash
cd backend
start.bat
```

### Option 2: Manual Setup

1. **Create virtual environment:**
```bash
cd backend
python -m venv venv
```

2. **Activate virtual environment:**

*Linux/Mac:*
```bash
source venv/bin/activate
```

*Windows:*
```bash
venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```
GEMINI_API_KEY=your_actual_api_key_here
```

5. **Run the server:**
```bash
python main.py
```

## Verify Installation

1. **Check health endpoint:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

2. **Access API documentation:**

Open browser: http://localhost:8000/docs

## Test the API

### Using curl:

```bash
curl -X POST http://localhost:8000/api/analyze-report \
  -F "file=@sample_report.pdf" \
  -H "accept: application/json"
```

### Using Python:

```python
import requests

with open('sample_report.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/analyze-report',
        files={'file': f}
    )

print(response.json())
```

### Using the Interactive Docs:

1. Go to: http://localhost:8000/docs
2. Click on `POST /api/analyze-report`
3. Click "Try it out"
4. Upload a file
5. Click "Execute"

## Expected Response Format

```json
{
  "summary": "One parameter is outside the normal range among 10 tests.",
  "urgency_level": "Monitor",
  "results": [
    {
      "parameter": "Hemoglobin",
      "value": 11.2,
      "unit": "g/dL",
      "status": "low",
      "explanation": "Low hemoglobin indicates reduced oxygen-carrying capacity in blood.",
      "reference_range": "12.0 - 16.0 g/dL"
    }
  ],
  "recommended_questions": [
    "Should I repeat this test?",
    "What lifestyle changes can help improve these values?"
  ]
}
```

## Troubleshooting

### Error: "GEMINI_API_KEY environment variable not set"
- Make sure you created the `.env` file
- Verify the API key is correct
- Restart the server after adding the key

### Error: "Connection refused"
- Check if the server is running
- Verify port 8000 is not blocked
- Try: `python main.py`

### Error: "No module named 'fastapi'"
- Activate virtual environment
- Run: `pip install -r requirements.txt`

## Next Steps

1. Test with your own lab reports (PDF or images)
2. Check the logs for processing details
3. Customize `reference_ranges.json` for additional parameters
4. Integrate with your frontend application

## Support

For issues or questions:
- Check the README.md for detailed documentation
- Review the API docs at http://localhost:8000/docs
- Examine server logs for error details
