# --- Import Necessary Libraries ---
import os
import time
import shutil
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# --- Import LangChain Components ---
# Used to interact with the Groq model
from langchain_groq import ChatGroq
# The main chain for retrieving documents and generating answers
from langchain.chains import create_retrieval_chain
# Used to stuff the retrieved documents into the prompt
from langchain.chains.combine_documents import create_stuff_documents_chain
# The prompt template for instructing the LLM
from langchain_core.prompts import ChatPromptTemplate
# The vector store for efficient similarity searches (FAISS from Facebook AI)
from langchain_community.vectorstores import FAISS
# The loader for processing PDF files from a directory
from langchain_community.document_loaders import PyPDFDirectoryLoader
# The embedding model from Google to convert text to vectors
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- Initial Setup and Configuration ---

# Load environment variables (API keys) from a .env file in the root directory
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) to allow requests from your frontend
CORS(app)

# --- Application Configuration ---
# This dictionary holds the application's state and settings.
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['VECTORS'] = None  # Will hold the FAISS vector store in memory
app.config['PDF_FILENAMES'] = [] # Will keep track of uploaded PDF names

# Create the 'uploads' directory if it doesn't already exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- API Key and LLM Initialization ---

# Retrieve API keys from environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

# CRITICAL: Set the Google API key as an environment variable for the library to use
os.environ['GOOGLE_API_KEY'] = google_api_key

# Fail-fast: Check for API keys on startup to prevent runtime errors
if not groq_api_key or not google_api_key:
    raise ValueError("API keys for Groq and Google are not set. Please check your .env file.")

# Initialize the ChatGroq model for fast inference
llm = ChatGroq(groq_api_key=groq_api_key, model_name="gemma2-9b-it")

# Create a prompt template to instruct the LLM on how to answer
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
    """
    Loads PDFs from a directory, splits them into chunks, creates embeddings,
    and stores them in a FAISS vector store.
    """
    # Initialize Google's embedding model.
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # Load all PDF files from the specified directory
    loader = PyPDFDirectoryLoader(directory)
    pages = loader.load_and_split() # Loads and splits into manageable chunks
    
    # If no documents were found in the PDFs, return None
    if not pages:
        return None
        
    # Create the FAISS vector store from the document chunks and their embeddings
    # This is the core of the RAG system's retrieval capability.
    vectors = FAISS.from_documents(pages, embeddings)
    return vectors

def clear_upload_folder():
    """Delete all files in the upload folder and reset the app state."""
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
            
    # Reset the application config state for the new session
    app.config['PDF_FILENAMES'] = []
    app.config['VECTORS'] = None


# --- API Routes (Endpoints) ---

@app.route('/')
def health_check():
    """A simple health check endpoint for deployment services."""
    return jsonify({"status": "healthy", "message": "API is running."}), 200

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle PDF file uploads, create the vector store, and save state."""
    clear_upload_folder() # Start fresh for each upload session
    
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
        # Generate and store the vector embeddings in the application's config
        print("Creating vector store...")
        app.config['VECTORS'] = vector_embedding(app.config['UPLOAD_FOLDER'])
        
        if app.config['VECTORS'] is None:
             return jsonify({"error": "Could not create vector store. The PDF might be empty or corrupted."}), 500
        
        print("Vector store created successfully.")
        return jsonify({"message": "Files uploaded and vector store ready", "uploaded_files": uploaded_filenames}), 200
    except Exception as e:
        # Catch any other errors during the embedding process
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

    # This chain combines the LLM and the prompt.
    document_chain = create_stuff_documents_chain(llm, prompt)
    # The retriever gets relevant documents from the vector store based on the question.
    retriever = vectors.as_retriever()
    # This final chain ties the retriever and the document_chain together.
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    start = time.process_time()
    # Invoke the chain with the user's question.
    response = retrieval_chain.invoke({'input': question})
    response_time = time.process_time() - start

    answer = response.get('answer', "Sorry, I couldn't find an answer.")
    
    # Safely get the context and format it for the frontend
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
        return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_name, as_attachment=False)
    except FileNotFoundError:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/get-pdf-names', methods=['GET'])
def get_pdf_names():
    """Return the list of currently uploaded PDF filenames."""
    return jsonify({"pdfNames": app.config['PDF_FILENAMES']}), 200

# --- Main Execution Block ---
# This block allows running the app locally for development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
