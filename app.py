import os
import shutil
import time
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# --- LangChain Imports ---
from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ----------------- ENVIRONMENT AND API KEY SETUP -----------------
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

if not groq_api_key or not google_api_key:
    raise ValueError("API keys for Groq and Google are not set. Please check your .env file.")

# ----------------- FLASK APP CONFIGURATION -----------------
app = Flask(__name__)

# --- Configuration Constants ---
PERSISTENT_DIR = "persistent_data"
PDF_UPLOAD_DIR = os.path.join(PERSISTENT_DIR, "uploads")
FAISS_INDEX_DIR = os.path.join(PERSISTENT_DIR, "faiss_indexes")
PDF_FILENAMES_PATH = os.path.join(PERSISTENT_DIR, "pdf_filenames.json")
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE_MB = 25 # Increased limit to 25MB

# Create persistent directories if they don't exist
os.makedirs(PDF_UPLOAD_DIR, exist_ok=True)
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


# ----------------- CORS (Cross-Origin Resource Sharing) SETUP -----------------
ALLOWED_ORIGINS = [
    "https://iqpdf.netlify.app",
    "http://localhost:3000"
]

CORS(app, resources={r"/*": {
    "origins": ALLOWED_ORIGINS,
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

@app.after_request
def after_request(response):
    """Ensure CORS headers are set for all responses."""
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

# ----------------- LANGCHAIN SETUP -----------------
llm = ChatGroq(groq_api_key=groq_api_key, model_name="gemma2-9b-it")
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate and detailed response based on the question and context.
    If the context does not contain the answer, state that "Based on the provided documents, I cannot answer this question."

    <context>
    {context}
    <context>
    
    Question: {input}
    """
)

# ----------------- HELPER FUNCTIONS -----------------
def allowed_file(filename):
    """Checks if a filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_pdf_filenames_from_disk():
    """Reads the list of uploaded PDF filenames from the JSON file."""
    if not os.path.exists(PDF_FILENAMES_PATH):
        return []
    try:
        with open(PDF_FILENAMES_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def update_pdf_filenames_on_disk(filename):
    """Adds a new filename to the JSON record, ensuring no duplicates."""
    current_files = get_pdf_filenames_from_disk()
    if filename not in current_files:
        current_files.append(filename)
        with open(PDF_FILENAMES_PATH, "w") as f:
            json.dump(current_files, f, indent=4)

def extract_text_from_pdf(filepath):
    """Extracts text from a single PDF file."""
    text = ""
    try:
        with open(filepath, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except Exception as e:
        app.logger.error(f"Error extracting text from {os.path.basename(filepath)}: {e}")
    return text

def create_and_save_embeddings(text_chunks, base_filename):
    """Generates embeddings and saves them to a FAISS index."""
    try:
        vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
        index_path = os.path.join(FAISS_INDEX_DIR, base_filename)
        vectorstore.save_local(index_path)
        app.logger.info(f"Successfully created and saved index for {base_filename}")
    except Exception as e:
        app.logger.error(f"Failed to create/save embeddings for {base_filename}: {e}")
        raise

def load_and_merge_vector_stores():
    """Loads all existing FAISS indexes and merges them into one."""
    pdf_filenames = get_pdf_filenames_from_disk()
    if not pdf_filenames:
        return None

    merged_store = None
    for filename in pdf_filenames:
        index_path = os.path.join(FAISS_INDEX_DIR, secure_filename(filename))
        if os.path.exists(index_path):
            try:
                if merged_store is None:
                    # Load the first index
                    merged_store = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
                else:
                    # Load subsequent indexes and merge
                    to_merge = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
                    merged_store.merge_from(to_merge)
                app.logger.info(f"Successfully loaded and merged index for {filename}")
            except Exception as e:
                app.logger.error(f"Could not load or merge index for {filename}. Skipping. Error: {e}")
                continue
    return merged_store


# ----------------- API ROUTES ------------------
@app.route("/", methods=["GET"])
def home():
    """Root endpoint to check if the backend is running."""
    return jsonify({"status": "Backend is running! 🚀"})

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handles PDF file uploads, processes them, and creates vector stores."""
    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    uploaded_files = request.files.getlist('files')
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({"error": "No files selected for uploading"}), 400
    
    processed_files = []
    errors = []

    for file in uploaded_files:
        if not (file and allowed_file(file.filename)):
            errors.append(f"Invalid file type: {file.filename}")
            continue

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            errors.append(f"File exceeds {MAX_FILE_SIZE_MB}MB limit: {file.filename}")
            continue

        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(PDF_UPLOAD_DIR, filename)
            file.save(filepath)

            # 1. Extract text
            text = extract_text_from_pdf(filepath)
            if not text:
                errors.append(f"Could not extract text from {filename}. It might be empty or image-based.")
                continue
            
            # 2. Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_text(text)
            
            # 3. Create and save embeddings
            create_and_save_embeddings(chunks, filename)
            
            # 4. Update the record of processed files
            update_pdf_filenames_on_disk(filename)
            processed_files.append(filename)

        except Exception as e:
            app.logger.error(f"Error processing {file.filename}: {e}")
            errors.append(f"An internal error occurred while processing {file.filename}.")
    
    if not processed_files and errors:
        return jsonify({"error": "Failed to process any files.", "details": errors}), 400

    return jsonify({
        "message": f"Successfully processed {len(processed_files)} file(s).",
        "processed_files": processed_files,
        "errors": errors
    }), 200

@app.route('/ask', methods=['POST'])
def ask_question():
    """Receives a question and returns an answer based on the merged vector stores."""
    vectors = load_and_merge_vector_stores()
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
        
        start_time = time.time()
        response = retrieval_chain.invoke({'input': question})
        response_time = time.time() - start_time

        answer = response.get('answer', "Sorry, I couldn't find an answer.")
        
        # Extract source documents from context
        context_sources = []
        if response.get("context"):
            for doc in response["context"]:
                metadata = doc.metadata
                source = os.path.basename(metadata.get("source", "Unknown"))
                page = int(metadata.get("page", -1)) + 1
                context_sources.append({"source": source, "page": page})
        
        # Remove duplicate sources
        unique_sources = [dict(t) for t in {tuple(d.items()) for d in context_sources}]
        
        return jsonify({
            "answer": answer,
            "response_time": f"{response_time:.2f}s",
            "context": unique_sources
        })

    except Exception as e:
        app.logger.error(f"Error during question asking: {e}")
        return jsonify({"error": "An error occurred while processing your question."}), 500

@app.route('/get-pdf/<path:pdf_name>', methods=['GET'])
def get_pdf(pdf_name):
    """Serves a specific PDF file from the upload directory."""
    safe_pdf_name = secure_filename(pdf_name)
    pdf_path = os.path.join(PDF_UPLOAD_DIR, safe_pdf_name)
    if os.path.exists(pdf_path):
        return send_from_directory(PDF_UPLOAD_DIR, safe_pdf_name)
    else:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/get-pdf-names', methods=['GET'])
def get_pdf_names():
    """Returns the list of all uploaded PDF filenames."""
    return jsonify({"pdfNames": get_pdf_filenames_from_disk()})

# ----------------- MAIN EXECUTION -------------------
if __name__ == '__main__':
    # For local development
    app.run(host='0.0.0.0', port=5000, debug=True)