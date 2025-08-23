import os
import shutil
import time
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- Environment and API Key Setup ---
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

if not groq_api_key or not google_api_key:
    raise ValueError("API keys (GROQ_API_KEY, GOOGLE_API_KEY) are not set. Please check your .env file.")

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Configuration ---
# Use a dedicated folder for persistent data. In production (e.g., on Render),
# this directory should be mounted to a persistent disk.
PERSISTENT_DATA_DIR = 'persistent_data'
PDF_UPLOAD_DIR = os.path.join(PERSISTENT_DATA_DIR, 'uploads')
FAISS_INDEX_PATH = os.path.join(PERSISTENT_DATA_DIR, 'faiss_index')
PDF_FILENAMES_PATH = os.path.join(PERSISTENT_DATA_DIR, 'pdf_filenames.json')

app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# --- Global Variables for In-Memory Cache ---
# These will be loaded from disk on startup if they exist.
vectors = None
pdf_filenames = []

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if a filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def initialize_app_state():
    """
    Loads the vector store and PDF filenames from disk if they exist.
    This function is called once on application startup.
    """
    global vectors, pdf_filenames
    
    # Create persistent directories if they don't exist
    os.makedirs(PDF_UPLOAD_DIR, exist_ok=True)
    
    try:
        # Load PDF filenames if the file exists
        if os.path.exists(PDF_FILENAMES_PATH):
            with open(PDF_FILENAMES_PATH, 'r') as f:
                pdf_filenames = json.load(f)
            app.logger.info(f"Loaded {len(pdf_filenames)} PDF filenames from disk.")

        # Load FAISS vector store if it exists
        if os.path.exists(FAISS_INDEX_PATH):
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vectors = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            app.logger.info("Successfully loaded FAISS vector store from disk.")
            
    except Exception as e:
        app.logger.error(f"Error initializing app state from disk: {e}")
        # If loading fails, clear the state to start fresh
        clear_persistent_data()

def clear_persistent_data():
    """
    Deletes all stored PDFs, the vector index, and the filenames list.
    """
    global vectors, pdf_filenames
    try:
        if os.path.exists(PERSISTENT_DATA_DIR):
            shutil.rmtree(PERSISTENT_DATA_DIR)
        
        # Recreate the necessary directories after clearing
        os.makedirs(PDF_UPLOAD_DIR, exist_ok=True)
        
        # Reset in-memory variables
        vectors = None
        pdf_filenames = []
        
        app.logger.info("Cleared all persistent data.")
    except Exception as e:
        app.logger.error(f"Failed to clear persistent data. Reason: {e}")

# --- LangChain Setup ---
llm = ChatGroq(groq_api_key=groq_api_key, model_name="gemma2-9b-it")
prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate response based on the question.
    <context>
    {context}
    <context>
    Questions:{input}
    """
)

# --- API Routes ---
@app.route("/")
def home():
    return "Backend is running 🚀"

@app.route('/upload', methods=['POST'])
def upload_files():
    global vectors, pdf_filenames
    
    if 'files' not in request.files:
        return jsonify({"error": "No files part"}), 400

    uploaded_files = request.files.getlist('files')
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({"error": "No selected files"}), 400

    # Before uploading new files, clear all previous data
    clear_persistent_data()
    
    uploaded_filenames = []
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(PDF_UPLOAD_DIR, filename)
            file.save(filepath)
            uploaded_filenames.append(filename)
        else:
            # If any file is invalid, stop the process
            clear_persistent_data()
            return jsonify({"error": f"File type not allowed for {file.filename}"}), 400

    try:
        # 1. Create vector embedding from the newly uploaded PDFs
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        loader = PyPDFDirectoryLoader(PDF_UPLOAD_DIR)
        pages = loader.load_and_split()
        
        if not pages:
             clear_persistent_data()
             return jsonify({"error": "Could not extract text from the provided PDF(s). They might be empty or corrupted."}), 400

        db = FAISS.from_documents(pages, embeddings)
        
        # 2. Save the new vector store and filenames to disk
        db.save_local(FAISS_INDEX_PATH)
        with open(PDF_FILENAMES_PATH, 'w') as f:
            json.dump(uploaded_filenames, f)
            
        # 3. Update the in-memory variables
        vectors = db
        pdf_filenames = uploaded_filenames
        
        app.logger.info("Files uploaded, vector store created and saved to disk.")
        return jsonify({
            "message": "Files uploaded and vector store ready",
            "uploaded_files": uploaded_filenames
        }), 200

    except Exception as e:
        app.logger.error(f"Error during vector embedding: {e}")
        clear_persistent_data()
        return jsonify({"error": "An error occurred while processing the files."}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    if not vectors:
        return jsonify({"error": "Vector store is not initialized. Please upload PDF files first."}), 400

    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = vectors.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)
        
        start = time.process_time()
        response = retrieval_chain.invoke({'input': question})
        response_time = time.process_time() - start

        answer = response.get('answer', "Sorry, I couldn't find an answer.")
        context = response.get("context")
        
        # Filter context only if an answer was found
        if "provided text does not contain any information" in answer or not context:
            context_sources = None
        else:
            context_sources = [
                {
                    "source": os.path.basename(doc.metadata.get("source", "Unknown")),
                    "page": int(doc.metadata.get("page", -1)) + 1
                } for doc in context
            ]

        return jsonify({
            "answer": answer,
            "response_time": response_time,
            "context": context_sources
        })

    except Exception as e:
        app.logger.error(f"Error during question asking: {e}")
        return jsonify({"error": "An error occurred while processing your question."}), 500

@app.route('/get-pdf/<path:pdf_name>', methods=['GET'])
def get_pdf(pdf_name):
    safe_pdf_name = secure_filename(pdf_name)
    pdf_path = os.path.join(PDF_UPLOAD_DIR, safe_pdf_name)
    if os.path.exists(pdf_path):
        return send_from_directory(PDF_UPLOAD_DIR, safe_pdf_name)
    else:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/get-pdf-names', methods=['GET'])
def get_pdf_names():
    return jsonify({"pdfNames": pdf_filenames})

# --- Main Execution ---
if __name__ == '__main__':
    # This block is for local development only.
    # Gunicorn will be used in production.
    initialize_app_state()
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # This block is executed when running with a production server like Gunicorn.
    initialize_app_state()

