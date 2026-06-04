# Spoiler Safe - Chrome Extension

A Chrome extension that allows you to ask spoiler-safe questions about YouTube videos you're currently watching. Powered by local LLM (Large Language Model) and RAG (Retrieval Augmented Generation) technology.

## Overview

**Spoiler Safe** is an intelligent assistant that answers questions about video content while respecting the current timestamp in the video. If you ask a question about something that happens later in the video, the assistant will avoid spoiling you and only reference content up to your current position.

### Features

- 🎬 **YouTube Integration**: Works seamlessly with YouTube videos
- 🔒 **Spoiler-Safe Responses**: Answers are contextualized to your current video position
- 🧠 **Local LLM**: Uses Ollama with Llama 3.1 for on-device processing (privacy-first)
- 📝 **RAG Technology**: Retrieval-Augmented Generation for accurate context-aware answers
- 💬 **Interactive Panel**: Clean UI within the YouTube page for asking questions
- 📊 **Transcript Analysis**: Utilizes video transcripts for accurate context building

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - For the backend server
- **Ollama** - For running the local LLM model
- **Chrome Browser** - For the extension
- **Git** - For cloning the repository

### Installing Ollama

1. Download Ollama from [https://ollama.ai](https://ollama.ai)
2. Install and run Ollama
3. Download the Llama 3.1 model:
   ```bash
   ollama pull llama3.1:8b
   ```

## Project Structure

```
chrome_extension/
├── backend/                 # FastAPI backend server
│   ├── __init__.py
│   ├── app.py              # Main FastAPI application
│   ├── llm.py              # LLM integration with Ollama
│   └── rag.py              # RAG and context building
├── extension/              # Chrome extension files
│   ├── manifest.json       # Extension configuration
│   ├── background.js       # Service worker
│   ├── content.js          # Content script for YouTube
│   ├── styles.css          # Extension styling
│   └── icons/              # Extension icons
├── backup/                 # Backup of original popup files
├── requirements.txt        # Python dependencies
├── steps to run            # Quick start guide
└── README.md              # This file
```

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/spoiler-safe.git
cd spoiler-safe
```

### 2. Set Up Python Virtual Environment

**On Windows (PowerShell):**
```powershell
# Allow venv scripts to run
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama (if not already installed)

1. Download from [https://ollama.ai](https://ollama.ai)
2. Install and run Ollama
3. Pull the Llama 3.1 model:
   ```bash
   ollama pull llama3.1:8b
   ```

## Running the Application

### Terminal 1: Start Ollama

```bash
ollama serve
```

The Ollama service will be available at `http://127.0.0.1:11434`

### Terminal 2: Start the Backend Server

```bash
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
Press CTRL+C to quit
```

### Terminal 3: Load the Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Navigate to the `extension/` folder in this project and select it
5. The Spoiler Safe extension should now appear in your extensions list

## Usage

1. Navigate to any YouTube video
2. Click the Spoiler Safe extension icon in your Chrome toolbar
3. A panel will appear on the right side of the page
4. Type your question about the video content
5. The extension will provide a spoiler-safe answer based on your current timestamp

## Configuration

### Environment Variables

You can customize the following settings by setting environment variables before running the backend:

```bash
# LLM Configuration
$env:OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
$env:OLLAMA_MODEL = "llama3.1:8b"
$env:OLLAMA_TIMEOUT_SECONDS = "120"
```

### Backend API Endpoints

- **GET `/health`** - Health check endpoint
- **POST `/ask`** - Ask a question about video content
  - Request body:
    ```json
    {
      "title": "Video Title",
      "video_id": "dQw4w9WgXcQ",
      "current_time": 120,
      "current_time_human": "2:00",
      "question": "What is the main topic?",
      "transcript": [
        {
          "start": 0,
          "dur": 5.5,
          "text": "Hello everyone..."
        }
      ]
    }
    ```

## Technology Stack

### Frontend (Chrome Extension)
- **Manifest V3** - Latest Chrome extension API
- **Vanilla JavaScript** - Content script and background service worker
- **CSS** - Responsive styling for the UI panel

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **Requests** - HTTP client for Ollama communication
- **Ollama** - Local LLM inference engine
- **Llama 3.1** - Open-source language model

## Key Features in Detail

### RAG (Retrieval-Augmented Generation)
The system uses RAG to build context from video transcripts, ensuring:
- Only relevant transcript segments are used
- Responses stay within character limits
- Context is always relative to the current video timestamp

### Spoiler-Safe Context Building
- Transcripts are filtered to only include content up to the current timestamp
- The LLM is prompted to avoid information beyond the current position
- Responses are validated for spoiler content

### Privacy First
- All LLM processing happens locally on your machine
- No data is sent to external APIs
- Ollama runs on your local system

## Troubleshooting

### Backend Server Won't Start
```bash
# Check if port 8000 is already in use
netstat -ano | findstr :8000

# Kill the process using that port (Windows)
taskkill /PID <PID> /F
```

### Ollama Connection Issues
1. Ensure Ollama is running: `ollama serve`
2. Check the connection: `curl http://127.0.0.1:11434/api/generate`
3. Verify the model is downloaded: `ollama list`

### Extension Not Showing in Chrome
1. Check `chrome://extensions/` for any error messages
2. Ensure the `extension/` folder is properly selected
3. Try refreshing the page (Ctrl+R) after reloading the extension
4. Check Chrome's developer console for JavaScript errors

### CORS Issues
The backend is configured with CORS enabled for all origins. If you still encounter issues:
1. Check the browser console for specific error messages
2. Ensure the backend is running on `http://127.0.0.1:8000`
3. Clear browser cache and reload the extension

## Development

### Making Changes

1. **Backend changes**: The `--reload` flag on uvicorn will automatically restart the server
2. **Extension changes**: 
   - Modify files in the `extension/` folder
   - Go to `chrome://extensions/` and click the refresh button on Spoiler Safe
   - Refresh the YouTube page

### Testing Endpoints

Use curl or Postman to test the backend:

```bash
# Health check
curl http://127.0.0.1:8000/health

# Ask endpoint (example)
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sample Video",
    "current_time": 60,
    "current_time_human": "1:00",
    "question": "What is this about?",
    "transcript": [
      {"start": 0, "dur": 60, "text": "Sample transcript content"}
    ]
  }'
```

## Recent Changes

### Version 2.0.0
- ✅ Upgraded to Manifest V3 (required by Chrome)
- ✅ Integrated FastAPI backend with RAG capabilities
- ✅ Added Ollama LLM integration
- ✅ Implemented spoiler-safe context filtering
- ✅ Added CORS support for cross-origin requests
- ✅ Improved UI with interactive panel
- ✅ Added health check endpoint
- ✅ Implemented transcript-based context building

### Previous Versions
- Initial Chrome extension with basic popup interface
- Single-file architecture

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Happy watching without spoilers!** 🎬🔒

