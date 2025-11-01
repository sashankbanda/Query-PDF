
# QueryPDF Setup Guide

Follow these steps to set up and run the QueryPDF application.

## Prerequisites

1. **Groq API Key**: Obtain from [Groq API Key](https://console.groq.com/playground).
2. **Google API Key**: Obtain from [Google API Key](https://ai.google.dev/gemini-api/docs/api-key).

## Environment Configuration

### Backend .env File
Create a `.env` file in the root directory of your project with the following content:

```plaintext
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```
Replace your_groq_api_key_here and your_google_api_key_here with your actual API keys.

### Frontend .env File
Create a .env file in the pdf-upload directory with the following content:

```plaintext
REACT_APP_API_URL=http://localhost:5000
```
This tells the React frontend where to find your Flask backend.

### System Dependencies
For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr libtesseract-dev poppler-utils
```
For macOS:
```bash
brew install tesseract poppler
```
For Windows:
Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki

Add Tesseract to your PATH

Install Poppler from: https://github.com/oschwartz10612/poppler-windows

## Backend Setup
Open a terminal.

Install the required Python packages:

```sh
pip install -r requirements.txt
```
Run the backend application:

```sh
python app.py
```
The backend will start on http://localhost:5000

## Frontend Setup
Open a new terminal.

Navigate to the `pdf-upload` directory:

```sh
cd pdf-upload
```
Install the required Node.js packages:

```sh
npm install
```
Start the frontend application:

```sh
npm start
```
The frontend will start on http://localhost:3000

## Features
✅ Text-based PDF processing

✅ Image-based PDF processing with OCR

✅ Chat interface for document queries

✅ Source citation with page numbers

✅ Dark/Light theme support

✅ Real-time upload progress

✅ Multiple PDF support

## Usage
Upload PDFs: Go to the home page and upload your PDF documents

Start Chat: After upload, you'll be redirected to the chat interface

Ask Questions: Type questions about your uploaded documents

View Sources: Click on citation links to jump to relevant PDF pages

## Troubleshooting
Common Issues:
CORS Errors: Ensure backend is running on port 5000 and frontend on port 3000

Upload Fails: Check that both .env files are properly configured

Image PDF Issues: Verify Tesseract OCR is installed correctly

Model Errors: Ensure your Groq API key is valid and has sufficient credits

## File Structure:
```text
your-project/
├── .env                    # Backend environment variables
├── app.py                  # Flask backend
├── requirements.txt        # Python dependencies
├── README.md
├── pdf-upload/
│   ├── .env               # Frontend environment variables
│   ├── package.json       # Node.js dependencies
│   └── src/
│       ├── App.js         # Main React app
│       ├── FileUpload.js  # File upload component
│       └── Chatbot.js     # Chat interface
└── uploads/               # Uploaded PDFs storage
```
## API Endpoints
POST /upload - Upload PDF files

POST /ask - Ask questions about documents

GET /get-pdf-names - Get list of uploaded PDFs

GET /get-pdf/<pdf_name> - Download specific PDF

## Technology Stack
Backend: Flask, Python, FAISS, HuggingFace Embeddings

Frontend: React.js, Axios

OCR: Tesseract, PyMuPDF

AI: Groq API, LangChain

Made with ❤️ by sashankbanda
