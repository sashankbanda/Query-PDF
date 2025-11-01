<a href="https://github.com/JoshuaThadi/JoshuaThadi/blob/main/fallout_grayscale%20(1).gif">
  <img src="https://github.com/JoshuaThadi/JoshuaThadi/blob/main/fallout_grayscale%20(1).gif" alt="Fallout GIF" style="width:auto; height:auto" />
</a>

# QueryPDF Setup Guide

Follow these steps to set up and run the QueryPDF application.

### 🔑 Prerequisites

1.  **Groq API Key**: Obtain from [Groq API Key](https://console.groq.com/playground).
2.  **Google API Key**: Obtain from [Google API Key](https://ai.google.dev/gemini-api/docs/api-key).

### ⚙️ Environment Configuration

#### Backend .env File
Create a `.env` file in the root directory of your project with the following content:

```plaintext
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```
Replace `your_groq_api_key_here` and `your_google_api_key_here` with your actual API keys.

#### Frontend .env File
Create a `.env` file in the `pdf-upload` directory with the following content:

```plaintext
REACT_APP_API_URL=http://localhost:5000
```
This tells the React frontend where to find your Flask backend.

#### System Dependencies
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

### 🚀 Backend Setup
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

### 🖥️ Frontend Setup
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

### ✨ Features
*   ✅ Text-based PDF processing
*   ✅ Image-based PDF processing with OCR
*   ✅ Chat interface for document queries
*   ✅ Source citation with page numbers
*   ✅ Dark/Light theme support
*   ✅ Real-time upload progress
*   ✅ Multiple PDF support

### 📝 Usage
*   Upload PDFs: Go to the home page and upload your PDF documents
*   Start Chat: After upload, you'll be redirected to the chat interface
*   Ask Questions: Type questions about your uploaded documents
*   View Sources: Click on citation links to jump to relevant PDF pages

### 🐛 Troubleshooting
Common Issues:
*   CORS Errors: Ensure backend is running on port 5000 and frontend on port 3000
*   Upload Fails: Check that both `.env` files are properly configured
*   Image PDF Issues: Verify Tesseract OCR is installed correctly
*   Model Errors: Ensure your Groq API key is valid and has sufficient credits

### 📁 File Structure
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

### 🌐 API Endpoints
*   `POST /upload` - Upload PDF files
*   `POST /ask` - Ask questions about documents
*   `GET /get-pdf-names` - Get list of uploaded PDFs
*   `GET /get-pdf/<pdf_name>` - Download specific PDF

### 💻 Technology Stack
<div align="center">
  <img src="https://img.shields.io/badge/Flask-%23000000.svg?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" />
  <img src="https://img.shields.io/badge/FAISS-blue?style=for-the-badge" alt="FAISS" />
  <img src="https://img.shields.io/badge/HuggingFace-%23D9B300.svg?style=for-the-badge&logo=huggingface&logoColor=white" alt="HuggingFace Embeddings" />
  <img src="https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB" alt="React.js" />
  <img src="https://img.shields.io/badge/axios-61DAFB?style=for-the-badge&logo=axios&logoColor=white" alt="Axios" />
  <img src="https://img.shields.io/badge/Tesseract_OCR-green?style=for-the-badge" alt="Tesseract" />
  <img src="https://img.shields.io/badge/PyMuPDF-red?style=for-the-badge" alt="PyMuPDF" />
  <img src="https://img.shields.io/badge/Groq_API-orange?style=for-the-badge" alt="Groq API" />
  <img src="https://img.shields.io/badge/LangChain-lightblue?style=for-the-badge" alt="LangChain" />
</div>

<a href="https://github.com/JoshuaThadi/Wall-E-Desk/blob/main/green.gif">
  <img src="https://github.com/JoshuaThadi/Wall-E-Desk/blob/main/Pixel-Art-2/green.gif" alt="Wall-E GIF" style="width:auto; height:auto" />
</a>

<img src="https://www.animatedimages.org/data/media/562/animated-line-image-0184.gif" width="100%" height="1" />

<p align="center">
  Made with ❤️ by <strong>sashankbanda</strong>
</p>