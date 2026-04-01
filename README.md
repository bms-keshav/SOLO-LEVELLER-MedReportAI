# MedReport AI 🏥

A full-stack health-tech application that transforms complex medical lab reports into clear, actionable insights using AI.

## 📁 Project Structure

```
pro/
├── frontend/           # Next.js React application
│   ├── app/
│   ├── package.json
│   └── ...
├── backend/            # FastAPI Python server
│   ├── main.py
│   ├── requirements.txt
│   └── ...
└── README.md          # This file
```

## 🚀 Quick Start

### 1️⃣ Start Backend (Terminal 1)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create a .env file with:
# GEMINI_API_KEY=your_gemini_api_key

# Run the server
python main.py
```

Backend will run at: **http://localhost:8000**

### 2️⃣ Start Frontend (Terminal 2)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will run at: **http://localhost:3000**

---

## 📚 Documentation

### Frontend (`/frontend`)
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Icons:** Lucide React
- **HTTP Client:** Axios

See [frontend/README.md](./frontend/README.md) for detailed frontend documentation.

### Backend (`/backend`)
- **Framework:** FastAPI
- **Language:** Python 3.10+
- **AI Engine:** Google Gemini API
- **PDF Processing:** PyPDF2
- **Image Processing:** Pillow

See [backend/README.md](./backend/README.md) for detailed backend documentation.

---

## ✨ Features

- 📤 **Drag-and-Drop Upload** - Intuitive file upload interface
- 🤖 **AI Analysis** - Powered by Google Gemini
- 📊 **Visual Dashboard** - Color-coded biomarker results
- 🚨 **Urgency Detection** - Normal, Monitor, or Consult Doctor
- 📱 **Mobile Responsive** - Works on all devices
- 🎯 **Demo Mode** - Test without uploading files

---

## 🔧 Development

### Frontend Development
```bash
cd frontend
npm run dev          # Start dev server
npm run build        # Production build
npm run lint         # Lint code
```

### Backend Development
```bash
cd backend
python main.py       # Start with auto-reload
python test_api.py   # Run API tests
```

---

## 🌐 API Endpoints

### Health Check
```
GET http://localhost:8000/health
```

### Analyze Report
```
POST http://localhost:8000/api/analyze-report
Content-Type: multipart/form-data

Body: file (PDF/JPG/PNG)
```

**Response:**
```json
{
  "urgency_level": "Normal" | "Monitor" | "Consult Doctor",
  "summary": "Overall analysis...",
  "results": [
    {
      "name": "Biomarker Name",
      "value": "123",
      "unit": "mg/dL",
      "status": "Normal" | "High" | "Low",
      "ai_explanation": "..."
    }
  ],
  "recommended_questions": ["Question 1?", "..."]
}
```

---

## 📦 Tech Stack

### Frontend
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Axios
- Lucide React

### Backend
- FastAPI
- Python 3.10+
- Google Gemini AI
- Pydantic
- Uvicorn
- PyPDF2 & Pillow

---

## 🔒 Environment Variables

### Frontend
No environment variables required for development.

### Backend
Create `backend/.env`:
```env
GEMINI_API_KEY=your_google_gemini_api_key
```

Get your API key from: [Google AI Studio](https://makersuite.google.com/app/apikey)

---

## 🚀 Deployment

### Frontend (Vercel)
```bash
cd frontend
npm run build
# Deploy to Vercel
```

### Backend (Railway/Render)
```bash
cd backend
# Deploy using Docker or direct Python deployment
```

**Important:** Update CORS settings in `backend/main.py` for production.

---

## 🧪 Testing

### Test Backend API
```bash
cd backend
python test_api.py
```

### Test Frontend
Use the "Load Sample Data (Demo)" button in the UI.

---

## 📄 License

MIT

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📞 Support

For issues and questions:
- Frontend issues: Check [frontend/README.md](./frontend/README.md)
- Backend issues: Check [backend/README.md](./backend/README.md)

---

Built with ❤️ for better health insights
