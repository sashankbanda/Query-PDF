# --- Import Necessary Libraries ---
import os
import time
import shutil
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import LangChain components
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- Initial Setup and Configuration ---

# Load environment variables (API keys) from a .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS)
CORS(app)

# --- Application Configuration ---
# Use the simpler, direct configuration from your original code
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['VECTORS'] = None
app.config['PDF_FILENAMES'] = []

# Create the 'uploads' directory if it doesn't already exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- API Key and LLM Initialization ---

# Retrieve API keys from the environment
groq_api_key = os.getenv("GROQ_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

# **CRITICAL FIX**: Set the Google API key as an environment variable
# This ensures the embedding model initializes correctly, matching your original code.
os.environ['GOOGLE_API_KEY'] = google_api_key

if not groq_api_key or not google_api_key:
    raise ValueError("API keys for Groq and Google are not set. Please check your environment variables.")

# Initialize the ChatGroq model
llm = ChatGroq(groq_api_key=groq_api_key, model_name="gemma2-9b-it")

# Create a prompt template to instruct the LLM
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

# --- Helper Functions ---

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension (PDF)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def vector_embedding(directory):
    """Load PDFs, split them, and create a FAISS vector store."""
    # Initialize Google's embedding model. It will now correctly find the API key.
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    loader = PyPDFDirectoryLoader(directory)
    pages = loader.load_and_split()
    if not pages:
        return None
    vectors = FAISS.from_documents(pages, embeddings)
    return vectors

def clear_upload_folder():
    """Delete all files in the upload folder to prepare for a new session."""
    folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
    # Reset the application config state
    app.config['PDF_FILENAMES'] = []
    app.config['VECTORS'] = None


# --- API Routes (Endpoints) ---

@app.route('/')
def health_check():
    """A simple health check endpoint for the deployment service (Render)."""
    return jsonify({"status": "healthy", "message": "API is running."}), 200

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle PDF file uploads, create vector store, and save state."""
    clear_upload_folder()
    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    uploaded_files = request.files.getlist('files')
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({"error": "No selected file"}), 400

    uploaded_filenames = []
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_filenames.append(filename)
        else:
            return jsonify({"error": f"File type not allowed for {file.filename}"}), 400
    
    app.config['PDF_FILENAMES'] = uploaded_filenames

    try:
        # Generate and store the vector embeddings
        app.config['VECTORS'] = vector_embedding(app.config['UPLOAD_FOLDER'])
        if app.config['VECTORS'] is None:
             return jsonify({"error": "Could not create vector embeddings. The PDF might be empty or corrupted."}), 500
        return jsonify({"message": "Files uploaded and vector store ready", "uploaded_files": uploaded_filenames}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred during embedding: {str(e)}"}), 500


@app.route('/ask', methods=['POST'])
def ask_question():
    """Receive a question, query the vector store, and return the LLM's answer."""
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    vectors = app.config.get('VECTORS')
    if not vectors:
        return jsonify({"error": "Vector store not initialized. Please upload PDF files first."}), 400

    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    start = time.process_time()
    response = retrieval_chain.invoke({'input': question})
    response_time = time.process_time() - start

    answer = response['answer']
    # Use the context formatting from your original code
    context = response.get("context")
    formatted_context = [{"source": doc.metadata["source"][8:], "page": int(doc.metadata["page"]) + 1} for doc in context] if context else None

    return jsonify({
        "answer": answer,
        "response_time": response_time,
        "context": formatted_context
    })

@app.route('/get-pdf/<path:pdf_name>', methods=['GET'])
def get_pdf(pdf_name):
    """Serve a specific PDF file from the uploads folder."""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_name)
    except FileNotFoundError:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/get-pdf-names', methods=['GET'])
def get_pdf_names():
    """Return the list of currently uploaded PDF filenames."""
    return jsonify({"pdfNames": app.config['PDF_FILENAMES']}), 200

# This block allows running the app locally for development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
