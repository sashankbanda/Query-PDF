# Query-PDF Application Updates

This document outlines all the changes and improvements made to the Query-PDF application.

## Table of Contents
1. [Citation System Fixes](#citation-system-fixes)
2. [API Configuration Fixes](#api-configuration-fixes)
3. [Embedding Model Migration](#embedding-model-migration)
4. [LLM Model Update](#llm-model-update)
5. [CORS Configuration](#cors-configuration)
6. [Error Handling Improvements](#error-handling-improvements)
7. [Dependencies Updates](#dependencies-updates)

---

## Citation System Fixes

### Issue
Citations were not accurately referencing PDF page numbers and file locations.

### Changes Made
- **File**: `app.py` (lines 161-197)
- Improved citation extraction from document metadata
- Added robust path normalization using `os.path.relpath()` with fallback to `os.path.basename()`
- Fixed page number handling to ensure 1-indexed display (converting from 0-indexed internal representation)
- Added validation for source paths and page numbers
- Implemented deduplication of citations using unique keys (source + page)

### Technical Details
```python
# Normalize file paths for consistent frontend display
source_name = os.path.relpath(source_path, uploads_dir)
source_name = source_name.replace("\\", "/")  # Windows path compatibility

# Convert 0-indexed to 1-indexed page numbers
page_display = page + 1 if page >= 0 else 1
```

### Result
Citations now accurately display:
- Correct PDF filename
- Accurate page numbers (1-indexed)
- Proper file path handling across different operating systems

---

## API Configuration Fixes

### Issue
Frontend was making requests to `undefined/upload` because `REACT_APP_API_URL` environment variable was not set.

### Changes Made
- **File**: `pdf-upload/src/config.js` (NEW FILE)
  - Created centralized API configuration file
  - Defaults to `http://localhost:5000` if environment variable is not set
  
- **Files Updated**:
  - `pdf-upload/src/FileUpload.js`
  - `pdf-upload/src/Chatbot.js`
  - Both now import and use `API_URL` from `config.js`

### Technical Details
```javascript
// config.js
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
export default API_URL;

// Usage in components
import API_URL from './config';
const response = await axios.post(`${API_URL}/upload`, formData);
```

### Result
- API calls now work correctly without requiring environment variable setup
- Centralized configuration makes it easy to change API URL if needed
- Fallback ensures application works out of the box

---

## Embedding Model Migration

### Issue
Google Generative AI Embeddings API quota exceeded (free tier limit: 0 requests).

### Changes Made
- **File**: `app.py` (lines 18-22, 58-87)
- Migrated from `GoogleGenerativeAIEmbeddings` to `HuggingFaceEmbeddings`
- Added support for new `langchain-huggingface` package with fallback to deprecated import
- Updated embedding model to `sentence-transformers/all-MiniLM-L6-v2`

### Technical Details
```python
# New embedding implementation
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)
```

### Benefits
- ✅ No API key required
- ✅ No quota limits
- ✅ Runs locally (no external API calls)
- ✅ Free and open-source
- ✅ Good performance for document embeddings

### Result
- Application no longer depends on Google API quotas
- Embeddings are generated locally, improving reliability
- First-time setup downloads model (~90MB) automatically

---

## LLM Model Update

### Issue
Groq model `gemma2-9b-it` was decommissioned and no longer supported.

### Changes Made
- **File**: `app.py` (line 44)
- Updated model from `gemma2-9b-it` to `llama-3.1-8b-instant`

### Technical Details
```python
# Old (decommissioned)
llm = ChatGroq(groq_api_key=groq_api_key, model_name="gemma2-9b-it")

# New (supported)
llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.1-8b-instant")
```

### Alternative Models Available
- `llama-3.1-8b-instant` (current) - Fast and efficient
- `mixtral-8x7b-32768` - Higher quality, larger context
- `llama-3.1-70b-versatile` - Best quality, slower

### Result
- Application now uses a supported, active model
- No more "model decommissioned" errors
- Improved response quality and speed

---

## CORS Configuration

### Issue
CORS errors blocking requests from React frontend to Flask backend, especially on `/ask` endpoint.

### Changes Made
- **File**: `app.py` (lines 27-30)
- Updated CORS configuration to be more permissive and explicit
- Changed from resource-based to direct configuration

### Technical Details
```python
# New CORS configuration
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"])
```

### Result
- All API endpoints now accessible from React frontend
- No more CORS policy errors
- Proper handling of preflight OPTIONS requests

---

## Error Handling Improvements

### Backend Error Handling

#### Upload Endpoint (`/upload`)
- **File**: `app.py` (lines 123-133)
- Added try-catch around vector embedding process
- Cleans up uploaded files if embedding fails
- Returns descriptive error messages

#### Ask Endpoint (`/ask`)
- **File**: `app.py` (lines 135-214)
- Wrapped entire endpoint in try-catch
- Specific error messages for different failure scenarios:
  - Model decommissioned errors
  - API quota/rate limit errors
  - Authentication errors
  - Generic errors with details

### Frontend Error Handling

#### FileUpload Component
- **File**: `pdf-upload/src/FileUpload.js` (lines 55-69)
- Improved error message extraction
- Distinguishes between server errors and network errors
- Better user feedback

#### Chatbot Component
- **File**: `pdf-upload/src/Chatbot.js` (lines 116-133)
- Enhanced error handling for question submission
- Clear error messages displayed to user
- Console logging for debugging

### Technical Details
```python
# Backend error handling example
except Exception as e:
    error_msg = str(e)
    if "model" in error_msg.lower() and "decommissioned" in error_msg.lower():
        return jsonify({"error": "The AI model has been updated. Please restart the server."}), 500
    elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
        return jsonify({"error": "API rate limit exceeded. Please try again later."}), 429
    # ... more specific error handling
```

```javascript
// Frontend error handling example
catch (error) {
    let errorText = 'Sorry, an error occurred.';
    if (error.response) {
        errorText = error.response.data.error || errorText;
    } else if (error.request) {
        errorText = 'Unable to connect to the server.';
    }
    // Display error to user
}
```

### Result
- Users receive clear, actionable error messages
- Better debugging capabilities
- Graceful error handling prevents application crashes
- Improved user experience

---

## Dependencies Updates

### New Dependencies Added
- **File**: `requirements.txt`
- `langchain-huggingface` - New package for HuggingFace embeddings
- `sentence-transformers` - Required for HuggingFace embeddings
- `torch` - PyTorch backend for sentence transformers

### Removed Dependencies
- `langchain_google_genai` - No longer needed after migration

### Updated Dependencies
All existing dependencies remain the same, ensuring compatibility.

### Installation
```bash
pip install -r requirements.txt
```

### Result
- Application now uses modern, supported packages
- No deprecated dependencies
- Better performance and reliability

---

## File Structure Changes

### New Files Created
1. `pdf-upload/src/config.js` - Centralized API configuration
2. `new_updates.md` - This documentation file

### Files Modified
1. `app.py` - Multiple improvements (citations, embeddings, model, CORS, error handling)
2. `pdf-upload/src/FileUpload.js` - API URL fix, error handling
3. `pdf-upload/src/Chatbot.js` - API URL fix, error handling
4. `requirements.txt` - Updated dependencies

---

## Migration Guide

### For Existing Users

1. **Update Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Restart Flask Server**
   - The model change requires a server restart
   - Old embeddings will be regenerated with new model

3. **No Frontend Changes Required**
   - React app will automatically use new configuration
   - Restart React dev server if needed

4. **Environment Variables**
   - `GROQ_API_KEY` - Still required for LLM
   - `GOOGLE_API_KEY` - No longer required (removed)
   - `REACT_APP_API_URL` - Optional (defaults to localhost:5000)

### First-Time Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Node dependencies (if not already done):
   ```bash
   cd pdf-upload
   npm install
   ```

3. Set up environment variables in `.env`:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. Start Flask backend:
   ```bash
   python app.py
   ```

5. Start React frontend:
   ```bash
   cd pdf-upload
   npm start
   ```

---

## Testing Checklist

After applying these updates, verify:

- [ ] PDF upload works without errors
- [ ] Citations display correct page numbers
- [ ] Citations show correct PDF filenames
- [ ] Chatbot responds to questions
- [ ] No CORS errors in browser console
- [ ] Error messages are clear and helpful
- [ ] Application works without Google API key

---

## Known Issues & Notes

### PDF Worker Warnings
- Browser console may show PDF.js worker warnings
- These are harmless and can be ignored
- They don't affect functionality

### First Embedding Generation
- First PDF upload may take longer
- HuggingFace model downloads automatically (~90MB)
- Subsequent uploads will be faster

### Model Performance
- `llama-3.1-8b-instant` is optimized for speed
- For better quality, consider switching to `mixtral-8x7b-32768` in `app.py`

---

## Summary of Benefits

✅ **More Reliable**: No dependency on external API quotas  
✅ **Better Citations**: Accurate page numbers and file references  
✅ **Improved UX**: Clear error messages and better feedback  
✅ **Easier Setup**: Works out of the box with sensible defaults  
✅ **Future-Proof**: Uses supported models and packages  
✅ **Better Maintainability**: Centralized configuration and error handling  

---

## Version Information

- **Update Date**: November 2025
- **Python Version**: 3.11+
- **Node Version**: Compatible with React 18+
- **LangChain Version**: Latest (with compatibility fallbacks)

---

## Support & Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Run: `pip install -r requirements.txt`

2. **CORS errors persist**
   - Ensure Flask server is running on port 5000
   - Check browser console for specific error

3. **Embedding generation fails**
   - Check internet connection (first-time model download)
   - Ensure sufficient disk space (~90MB for model)

4. **Model errors**
   - Verify `GROQ_API_KEY` is set correctly
   - Check Groq API status and quotas

---

## Future Improvements (Optional)

- [ ] Add support for multiple embedding models (configurable)
- [ ] Implement embedding caching to speed up subsequent uploads
- [ ] Add batch processing for multiple PDFs
- [ ] Implement streaming responses for better UX
- [ ] Add support for other file formats (DOCX, TXT, etc.)

---

*Last Updated: November 2025*

