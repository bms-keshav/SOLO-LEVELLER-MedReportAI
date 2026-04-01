'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import {
  Upload,
  FileText,
  Activity,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Cross,
  Loader2,
  XCircle,
} from 'lucide-react'

type AppState = 'idle' | 'loading' | 'success' | 'error'

type Biomarker = {
  name: string
  value: string
  unit: string
  status: 'Normal' | 'High' | 'Low'
  ai_explanation: string
}

type AnalysisResult = {
  urgency_level: 'Normal' | 'Monitor' | 'Consult Doctor'
  summary: string
  results: Biomarker[]
  recommended_questions: string[]
}

type BackendBiomarker = {
  parameter?: string
  name?: string
  value: number | string
  unit: string
  status: 'normal' | 'high' | 'low' | 'Normal' | 'High' | 'Low'
  explanation?: string
  ai_explanation?: string
}

type BackendAnalysisResult = {
  urgency_level: 'Normal' | 'Monitor' | 'Consult Doctor'
  summary: string
  results: BackendBiomarker[]
  recommended_questions: string[]
}

const normalizeStatus = (status: BackendBiomarker['status']): Biomarker['status'] => {
  const normalized = String(status).toLowerCase()
  if (normalized === 'high') return 'High'
  if (normalized === 'low') return 'Low'
  return 'Normal'
}

const normalizeAnalysisResult = (data: BackendAnalysisResult): AnalysisResult => ({
  urgency_level: data.urgency_level,
  summary: data.summary,
  recommended_questions: data.recommended_questions,
  results: data.results.map((result) => ({
    name: result.name ?? result.parameter ?? 'Unknown Parameter',
    value: String(result.value),
    unit: result.unit,
    status: normalizeStatus(result.status),
    ai_explanation:
      result.ai_explanation ??
      result.explanation ??
      'No explanation available for this parameter.',
  })),
})

const LOADING_MESSAGES = [
  'Scanning document...',
  'Extracting biomarkers...',
  'Running clinical rule engine...',
  'Simplifying medical jargon...',
]

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const MOCK_RESPONSE: AnalysisResult = {
  urgency_level: 'Monitor',
  summary:
    'Your lab results show several biomarkers that require attention. Your cholesterol levels are elevated, which may increase cardiovascular risk. Vitamin D is slightly low, which could affect bone health and immunity. Glucose levels are within normal range, indicating good metabolic function. Overall, these findings suggest lifestyle modifications and possible supplementation may be beneficial.',
  results: [
    {
      name: 'Total Cholesterol',
      value: '245',
      unit: 'mg/dL',
      status: 'High',
      ai_explanation:
        'Elevated total cholesterol increases risk of heart disease. Consider dietary changes, exercise, and consulting your doctor about statin therapy.',
    },
    {
      name: 'LDL Cholesterol',
      value: '160',
      unit: 'mg/dL',
      status: 'High',
      ai_explanation:
        'High LDL ("bad" cholesterol) can lead to plaque buildup in arteries. Reduce saturated fats and increase fiber intake.',
    },
    {
      name: 'HDL Cholesterol',
      value: '45',
      unit: 'mg/dL',
      status: 'Normal',
      ai_explanation:
        'HDL is within the normal range in this example. Keeping up regular exercise and balanced nutrition can help maintain it.',
    },
    {
      name: 'Triglycerides',
      value: '180',
      unit: 'mg/dL',
      status: 'High',
      ai_explanation:
        'Triglycerides are above the normal range in this example. This can happen with diet, weight, or metabolic factors and is worth reviewing with your doctor.',
    },
    {
      name: 'Fasting Glucose',
      value: '92',
      unit: 'mg/dL',
      status: 'Normal',
      ai_explanation:
        'Blood sugar levels are normal, indicating good glucose metabolism and low diabetes risk at this time.',
    },
    {
      name: 'Vitamin D',
      value: '22',
      unit: 'ng/mL',
      status: 'Low',
      ai_explanation:
        'Vitamin D deficiency can affect bone density and immune function. Consider supplementation (1000-2000 IU daily) and safe sun exposure.',
    },
    {
      name: 'Hemoglobin A1C',
      value: '5.4',
      unit: '%',
      status: 'Normal',
      ai_explanation:
        'Excellent long-term blood sugar control. This indicates low risk for diabetes and good metabolic health.',
    },
    {
      name: 'TSH (Thyroid)',
      value: '2.8',
      unit: 'mIU/L',
      status: 'Normal',
      ai_explanation:
        'Thyroid function is normal. Your metabolism and energy regulation are working properly.',
    },
  ],
  recommended_questions: [
    'Should I start taking a statin medication for my cholesterol?',
    'What dietary changes can help lower my LDL cholesterol?',
    'How much Vitamin D should I supplement daily?',
    'Do I need a follow-up lipid panel, and when?',
    'Are there any lifestyle interventions I should prioritize?',
  ],
}

export default function Home() {
  const [appState, setAppState] = useState<AppState>('idle')
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0])
  const [showWakeupHint, setShowWakeupHint] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const demoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wakeupHintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearPendingTimers = useCallback(() => {
    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current)
      resetTimerRef.current = null
    }
    if (demoTimerRef.current) {
      clearTimeout(demoTimerRef.current)
      demoTimerRef.current = null
    }
    if (wakeupHintTimerRef.current) {
      clearTimeout(wakeupHintTimerRef.current)
      wakeupHintTimerRef.current = null
    }
  }, [])

  // Cycle loading messages
  useEffect(() => {
    if (appState === 'loading') {
      let index = 0
      const interval = setInterval(() => {
        index = (index + 1) % LOADING_MESSAGES.length
        setLoadingMessage(LOADING_MESSAGES[index])
      }, 2500)
      return () => clearInterval(interval)
    }
  }, [appState])

  useEffect(() => {
    return () => {
      clearPendingTimers()
    }
  }, [clearPendingTimers])

  const handleFileUpload = async (file: File) => {
    if (!file) return
    clearPendingTimers()

    // Validate file type
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
    const lowerName = file.name.toLowerCase()
    const hasValidExtension =
      lowerName.endsWith('.pdf') ||
      lowerName.endsWith('.jpg') ||
      lowerName.endsWith('.jpeg') ||
      lowerName.endsWith('.png')
    if (!(validTypes.includes(file.type) || hasValidExtension)) {
      setErrorMessage('Please upload a PDF, JPG, or PNG file.')
      setAppState('error')
      resetTimerRef.current = setTimeout(() => setAppState('idle'), 3000)
      return
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('File size must be less than 10MB.')
      setAppState('error')
      resetTimerRef.current = setTimeout(() => setAppState('idle'), 3000)
      return
    }

    setAppState('loading')
    setErrorMessage('')
    setShowWakeupHint(false)

    wakeupHintTimerRef.current = setTimeout(() => {
      setShowWakeupHint(true)
      wakeupHintTimerRef.current = null
    }, 15000)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post<BackendAnalysisResult>(
        `${API_URL}/api/analyze-report`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 120000, // 120 second timeout for cold starts
        }
      )

      clearPendingTimers()
      setShowWakeupHint(false)
      setAnalysisResult(normalizeAnalysisResult(response.data))
      setAppState('success')
    } catch (error) {
      clearPendingTimers()
      setShowWakeupHint(false)

      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          setErrorMessage('Request timed out. Please try again.')
        } else if (error.response) {
          const backendDetail = error.response.data?.detail
          const backendMessage = error.response.data?.message
          setErrorMessage(
            `Server error: ${backendDetail || backendMessage || 'Analysis failed'}`
          )
        } else if (error.request) {
          setErrorMessage(
            'Cannot reach the server. Please ensure the backend is running on localhost:8000.'
          )
        } else {
          setErrorMessage('An unexpected error occurred.')
        }
      } else {
        setErrorMessage('Failed to analyze report. Please try again.')
      }
      setAppState('error')
      resetTimerRef.current = setTimeout(() => setAppState('idle'), 5000)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFileUpload(file)
  }

  const loadDemoData = () => {
    clearPendingTimers()
    setShowWakeupHint(false)
    setAppState('loading')
    demoTimerRef.current = setTimeout(() => {
      setAnalysisResult(MOCK_RESPONSE)
      setAppState('success')
      demoTimerRef.current = null
    }, 1500)
  }

  const resetApp = () => {
    clearPendingTimers()
    setShowWakeupHint(false)
    setAppState('idle')
    setAnalysisResult(null)
    setErrorMessage('')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'High':
        return <TrendingUp className="w-5 h-5 text-red-500" />
      case 'Low':
        return <TrendingDown className="w-5 h-5 text-orange-500" />
      case 'Normal':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      default:
        return <Minus className="w-5 h-5 text-gray-400" />
    }
  }

  const getUrgencyStyles = (level: string) => {
    switch (level) {
      case 'Normal':
        return 'bg-green-100 border-green-300 text-green-800'
      case 'Monitor':
        return 'bg-yellow-100 border-yellow-300 text-yellow-800'
      case 'Consult Doctor':
        return 'bg-red-100 border-red-300 text-red-800'
      default:
        return 'bg-gray-100 border-gray-300 text-gray-800'
    }
  }

  return (
    <main className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Hero Header */}
        <header className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="relative">
              <Cross className="w-10 h-10 text-teal-600" strokeWidth={2.5} />
              <Activity className="w-5 h-5 text-teal-500 absolute top-2 left-2" />
            </div>
            <h1 className="text-5xl font-bold bg-gradient-to-r from-teal-600 to-teal-800 bg-clip-text text-transparent">
              MedReport AI
            </h1>
          </div>
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Translating complex lab reports into actionable insights.
          </p>
        </header>

        {/* Upload State (Idle) */}
        {appState === 'idle' && (
          <div className="space-y-6 animate-in fade-in duration-500">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`
                relative border-3 border-dashed rounded-xl p-12 sm:p-16
                transition-all duration-300 ease-in-out
                ${
                  isDragging
                    ? 'border-teal-500 bg-teal-50 scale-105'
                    : 'border-teal-300 bg-white hover:border-teal-400 hover:bg-teal-50/50'
                }
                shadow-lg hover:shadow-xl cursor-pointer
              `}
            >
              <input
                type="file"
                id="fileInput"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileInputChange}
                className="hidden"
              />
              <label htmlFor="fileInput" className="cursor-pointer block">
                <div className="flex flex-col items-center gap-4">
                  <div className="p-4 bg-teal-100 rounded-full">
                    <Upload className="w-12 h-12 text-teal-600" />
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-semibold text-gray-700 mb-2">
                      {isDragging ? 'Drop your file here' : 'Upload Lab Report'}
                    </p>
                    <p className="text-gray-500 text-sm">
                      Drag & drop or click to browse
                    </p>
                    <p className="text-gray-400 text-xs mt-2">
                      Supports PDF, JPG, PNG (Max 10MB)
                    </p>
                  </div>
                </div>
              </label>
            </div>

            {/* Demo Button */}
            <div className="text-center">
              <button
                onClick={loadDemoData}
                className="text-xs text-gray-400 hover:text-teal-600 transition-colors underline"
              >
                Load Sample Data (Demo)
              </button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {appState === 'loading' && (
          <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-500">
            <div className="relative">
              <Loader2 className="w-16 h-16 text-teal-600 animate-spin" />
              <Activity className="w-8 h-8 text-teal-400 absolute top-4 left-4 animate-pulse" />
            </div>
            <p className="mt-6 text-xl font-medium text-gray-700 animate-pulse">
              {loadingMessage}
            </p>
            {showWakeupHint && (
              <p className="mt-3 text-sm text-gray-500">
                Waking up server and AI services. This can take up to a minute on first request.
              </p>
            )}
          </div>
        )}

        {/* Error State */}
        {appState === 'error' && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 animate-in fade-in duration-300">
            <div className="flex items-start gap-3">
              <XCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-900 mb-1">Analysis Failed</h3>
                <p className="text-red-700 text-sm">{errorMessage}</p>
              </div>
            </div>
          </div>
        )}

        {/* Success State - Results Dashboard */}
        {appState === 'success' && analysisResult && (
          <div className="space-y-6 animate-in fade-in duration-500">
            {/* Urgency Banner */}
            <div
              className={`
                border-2 rounded-xl p-6 shadow-md
                ${getUrgencyStyles(analysisResult.urgency_level)}
              `}
            >
              <div className="flex items-center gap-3">
                {analysisResult.urgency_level === 'Normal' && (
                  <CheckCircle className="w-8 h-8" />
                )}
                {analysisResult.urgency_level === 'Monitor' && (
                  <AlertTriangle className="w-8 h-8" />
                )}
                {analysisResult.urgency_level === 'Consult Doctor' && (
                  <AlertCircle className="w-8 h-8" />
                )}
                <div>
                  <p className="text-sm font-medium uppercase tracking-wide">
                    Urgency Level
                  </p>
                  <p className="text-2xl font-bold">
                    {analysisResult.urgency_level}
                  </p>
                </div>
              </div>
            </div>

            {/* Summary Card */}
            <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-100">
              <div className="flex items-start gap-3 mb-4">
                <FileText className="w-6 h-6 text-teal-600 flex-shrink-0 mt-1" />
                <h2 className="text-2xl font-bold text-gray-800">
                  Report Summary
                </h2>
              </div>
              <p className="text-gray-700 leading-relaxed">
                {analysisResult.summary}
              </p>
            </div>

            {/* Biomarker Grid */}
            <div>
              <h2 className="text-2xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <Activity className="w-6 h-6 text-teal-600" />
                Biomarker Details
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysisResult.results.map((biomarker, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-xl shadow-md p-6 border border-gray-100 hover:shadow-lg transition-shadow duration-200"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-800 text-lg">
                          {biomarker.name}
                        </h3>
                        <p className="text-2xl font-bold text-teal-600 mt-1">
                          {biomarker.value}{' '}
                          <span className="text-sm text-gray-500">
                            {biomarker.unit}
                          </span>
                        </p>
                      </div>
                      {getStatusIcon(biomarker.status)}
                    </div>
                    <div
                      className={`
                      inline-block px-3 py-1 rounded-full text-xs font-medium mb-3
                      ${
                        biomarker.status === 'Normal'
                          ? 'bg-green-100 text-green-700'
                          : biomarker.status === 'High'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-orange-100 text-orange-700'
                      }
                    `}
                    >
                      {biomarker.status}
                    </div>
                    <p className="text-sm text-gray-600 leading-relaxed">
                      {biomarker.ai_explanation}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Next Steps */}
            <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-100">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                Questions to Ask Your Doctor
              </h2>
              <ul className="space-y-3">
                {analysisResult.recommended_questions.map((question, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center flex-shrink-0 mt-0.5 font-semibold text-sm">
                      {index + 1}
                    </div>
                    <p className="text-gray-700">{question}</p>
                  </li>
                ))}
              </ul>
            </div>

            {/* Reset Button */}
            <div className="text-center pt-4">
              <button
                onClick={resetApp}
                className="px-8 py-3 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transition-all duration-200"
              >
                Analyze Another Report
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
