# MedReport AI - Frontend 🎨

Beautiful, responsive Next.js frontend for medical lab report analysis.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

## 🛠️ Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client for API calls
- **Lucide React** - Premium icon library

## 📁 Project Structure

```
frontend/
├── app/
│   ├── page.tsx          # Main application page
│   ├── layout.tsx        # Root layout
│   └── globals.css       # Global styles
├── package.json
├── tailwind.config.js    # Tailwind configuration
├── tsconfig.json         # TypeScript configuration
└── next.config.js        # Next.js configuration
```

## 🎯 Features

### Single-Page Architecture
- **Conditional Rendering** - All states on one page
- **State Flow:** idle → loading → success/error
- **No routing complexity** - Pure component logic

### UI Components

#### 1. Hero/Header
- Medical cross icon with Activity indicator
- Clean "MedReport AI" branding
- Professional tagline

#### 2. Upload State (Idle)
- Drag-and-drop file zone
- Teal accent colors (`text-teal-600`, `border-teal-300`)
- File validation (PDF, JPG, PNG, max 10MB)
- Hover effects and animations

#### 3. Loading State
- Animated spinner with pulsing effect
- Dynamic messages cycling every 2.5 seconds:
  - "Scanning document..."
  - "Extracting biomarkers..."
  - "Running clinical rule engine..."
  - "Simplifying medical jargon..."

#### 4. Results Dashboard (Success)

**Urgency Banner:**
- Color-coded: Green (Normal), Yellow (Monitor), Red (Consult Doctor)
- Full-width alert with appropriate icons

**Summary Card:**
- Elevated white card with shadow
- AI-generated health summary

**Biomarker Grid:**
- Responsive 2-column layout (mobile: 1-column)
- Each card shows:
  - Parameter name
  - Value + unit
  - Status icon (CheckCircle, AlertTriangle, TrendingUp/Down)
  - Color-coded status badge
  - AI explanation text

**Next Steps:**
- Numbered checklist of recommended questions
- Action-oriented format

#### 5. Demo Mode
- Subtle "Load Sample Data" button
- Comprehensive mock response
- Instant state transition to success

### Error Handling
- Network errors (backend unreachable)
- Timeout errors (120s timeout)
- Server errors (500, etc.)
- File validation errors
- Auto-dismissal after 5 seconds

## 🎨 Design System

### Colors
```javascript
Teal Palette:
- Primary: #0d9488 (teal-600)
- Light: #5eead4 (teal-300)
- Background: #f0fdfa (teal-50)

Status Colors:
- Normal: Green (#10b981)
- Monitor: Yellow (#f59e0b)
- Consult: Red (#ef4444)
- High: Red (#ef4444)
- Low: Orange (#f97316)
```

### Typography
- Font: Inter (Google Fonts)
- Headings: Bold, large scale
- Body: Regular, readable line-height

### Spacing & Layout
- Max width: 6xl (1280px)
- Padding: Responsive (4-8 units)
- Gaps: Consistent 4/6/8 units
- Rounded corners: xl (12px)

### Shadows
- Cards: `shadow-lg`
- Hover: `shadow-xl`
- Elevation for hierarchy

## 🔌 API Integration

### Endpoint
```typescript
POST http://localhost:8000/api/analyze-report
Content-Type: multipart/form-data
```

### Request
```typescript
FormData {
  file: File (PDF/JPG/PNG)
}
```

### Response
```typescript
{
  urgency_level: 'Normal' | 'Monitor' | 'Consult Doctor'
  summary: string
  results: Array<{
    parameter: string
    value: number
    unit: string
    status: 'normal' | 'high' | 'low'
    explanation: string
  }>
  recommended_questions: string[]
}
```

Note: The frontend also accepts legacy keys (`name`, `ai_explanation`) for compatibility.

### Error Handling
- Axios interceptors for global errors
- Timeout: 120 seconds
- CORS enabled on backend
- Retry logic not implemented (graceful failure instead)

## 📱 Responsive Design

### Breakpoints (Tailwind)
- `sm:` 640px (mobile landscape)
- `md:` 768px (tablets)
- `lg:` 1024px (desktop)

### Mobile Optimizations
- Single-column biomarker grid
- Reduced padding/margins
- Touch-friendly button sizes
- Responsive text sizes

## 🧪 Testing

### Manual Testing
1. **File Upload:**
   - Drag & drop
   - Click to browse
   - Invalid file types
   - Large files (>10MB)

2. **Loading State:**
   - Message cycling (2.5s intervals)
   - Spinner animation

3. **Success State:**
   - Urgency banner colors
   - Biomarker cards
   - Icons matching status
   - Responsive grid

4. **Demo Mode:**
   - Click "Load Sample Data"
   - Verify all data displays correctly

5. **Error Handling:**
   - Backend offline
   - Network issues
   - Invalid responses

### Browser Testing
- Chrome ✅
- Firefox ✅
- Safari ✅
- Edge ✅
- Mobile browsers ✅

## 🚀 Build & Deploy

### Development
```bash
npm run dev
# http://localhost:3000
```

### Production Build
```bash
npm run build
npm start
```

### Deploy to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

**Note:** Update API endpoint from `localhost:8000` to production URL.

## 🔧 Configuration

### Environment Variables
For production, create `.env.local`:
```env
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

Update `app/page.tsx`:
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

### Tailwind Customization
Edit `tailwind.config.js` to customize colors, spacing, or add plugins.

### TypeScript Configuration
`tsconfig.json` is pre-configured for Next.js App Router.

## 📦 Dependencies

```json
{
  "next": "^14.2.3",
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "axios": "^1.7.2",
  "lucide-react": "^0.379.0"
}
```

## 🎓 Best Practices

### Code Organization
- Single-page component (no routing)
- TypeScript for type safety
- React hooks for state management
- Axios for API calls

### Performance
- Next.js automatic code splitting
- Image optimization (if needed)
- Lazy loading not needed (single page)

### Accessibility
- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Screen reader friendly

### Security
- File type validation
- File size limits
- No sensitive data in frontend
- HTTPS in production

## 🐛 Troubleshooting

### Backend Connection Failed
- Ensure backend is running on port 8000
- Check CORS configuration
- Verify network/firewall settings

### Build Errors
```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build
```

### Styling Issues
```bash
# Rebuild Tailwind
npm run dev
```

## 📄 License

MIT

---

**Happy coding!** 🚀

For backend documentation, see [../backend/README.md](../backend/README.md)
