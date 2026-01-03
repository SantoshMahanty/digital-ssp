# Digital-SSP Test UI

Standalone HTML/CSS/JavaScript interfaces for testing and interacting with the Digital-SSP ad server.

## 📁 Files

### 1. **index.html** - Ad Request Tester
Interactive form to test ad requests with customizable parameters:
- Configure ad unit, sizes, geo, device
- Set key-value targeting
- Send requests to FastAPI backend
- View responses with detailed metrics
- Request history tracking

### 2. **inspector.html** - Ad Inspector
Debug and troubleshoot ad decisions:
- Look up requests by ID
- View decision trace timeline
- See why line items were filtered
- Identify no-fill reasons
- Copy trace data for analysis

### 3. **dashboard.html** - Overview Dashboard
Mock analytics and system monitoring:
- Key delivery metrics (requests, fill rate, eCPM)
- Active line items with pacing status
- Top performing ad units
- Geographic performance breakdown
- System health indicators
- Recent activity timeline

### 4. **assets/styles.css** - Shared Styles
Common stylesheet with:
- Professional design system
- Responsive grid layouts
- Form components
- Tables and badges
- Cards and alerts
- Timeline components

## 🚀 Quick Start

### Option 1: Open Directly in Browser
Simply double-click any HTML file to open in your default browser.

### Option 2: Serve with Python
```bash
cd test-ui
python -m http.server 8080
```
Then visit: `http://localhost:8080`

### Option 3: Serve with Node.js
```bash
cd test-ui
npx serve
```

## 🔧 Configuration

Each UI stores its API endpoint configuration in `localStorage`:
- **Ad Tester**: Default `http://localhost:8000/ad`
- **Inspector**: Default `http://localhost:8000/debug`

Update the API endpoint in the UI to match your backend server.

## 📝 Usage Examples

### Testing an Ad Request
1. Open `index.html`
2. Configure ad unit: `news/home/hero`
3. Select geo: `US`, device: `desktop`
4. Add sizes: `[{"w": 970, "h": 250}]`
5. Set key-values: `{"category": "news"}`
6. Click "Send Ad Request"
7. View winner details or no-fill reason

### Inspecting a Decision
1. Copy request ID from ad tester response
2. Open `inspector.html`
3. Paste request ID
4. Click "Inspect"
5. Review decision steps and filters applied

### Monitoring Performance
1. Open `dashboard.html`
2. View mock metrics and line item status
3. Check geographic breakdown
4. Review recent activity timeline

## 🎨 Features

- **No Dependencies**: Pure HTML/CSS/JavaScript
- **Responsive Design**: Works on desktop, tablet, mobile
- **Local Storage**: Saves settings and history
- **Clean UI**: Professional design inspired by modern ad platforms
- **Easy Integration**: Works with any REST API backend
- **Copy/Paste Ready**: Easy to share request/response data

## 🔌 API Requirements

The test UIs expect the following API endpoints:

### POST /ad
Ad decisioning endpoint
```json
{
  "adUnit": "string",
  "sizes": [{"w": number, "h": number}],
  "kv": {"key": "value"},
  "geo": "string",
  "device": "string",
  "userId": "string?",
  "viewportW": number?
}
```

Returns:
```json
{
  "source": "internal|dsp",
  "price": number,
  "line_item_id": "string",
  "creative_id": "string",
  "req_id": "string"
}
```

### GET /debug/{req_id}
Decision trace endpoint

Returns:
```json
{
  "req_id": "string",
  "winner": {...} | null,
  "no_fill_reason": "string?",
  "steps": [
    {
      "step": "string",
      "detail": "string",
      "data": any
    }
  ]
}
```

## 📱 Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🎯 Use Cases

- **Development**: Test ad decisioning logic during development
- **QA**: Verify targeting, pacing, and floor price rules
- **Demos**: Show SSP functionality to stakeholders
- **Training**: Learn how ad servers make decisions
- **Debugging**: Troubleshoot no-fill scenarios

## 🔐 CORS Configuration

If your API runs on a different port, enable CORS in your FastAPI app:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📄 License

Part of the Digital-SSP project - Educational use only.
