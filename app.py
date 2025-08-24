import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import time
import shutil

from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys from environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

# It's good practice to ensure API keys are available when the app starts.
if not groq_api_key or not google_api_key:
    raise ValueError("API keys for Groq and Google are not set. Please check your environment variables.")

app = Flask(__name__)
CORS(app)

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
# Use a dictionary to store session-specific data in memory
# This is a simple approach; for larger apps, consider Redis or a database.
app.config['STATE'] = {
    "vectors": None,
    "pdf_filenames": []
}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- LLM and Prompt Initialization ---
llm = ChatGroq(groq_api_key=groq_api_key, model_name="gemma2-9b-it")

prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate response based on the question.
    If the answer is not in the context, say "The provided text does not contain information about this."
    <context>
    {context}
    <context>
    Questions:{input}
    """
)

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def vector_embedding(directory):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)
    loader = PyPDFDirectoryLoader(directory)
    pages = loader.load_and_split()
    # Handle case where no documents are loaded
    if not pages:
        return None
    vectors = FAISS.from_documents(pages, embeddings)
    return vectors

def clear_upload_folder():
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
    # Clear the state
    app.config['STATE']['pdf_filenames'] = []
    app.config['STATE']['vectors'] = None


# --- API Routes ---

@app.route('/')
def health_check():
    """Health check endpoint for Render."""
    return jsonify({"status": "healthy", "message": "API is running."}), 200

@app.route('/upload', methods=['POST'])
def upload_files():
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

    try:
        vectors = vector_embedding(app.config['UPLOAD_FOLDER'])
        if vectors is None:
             return jsonify({"error": "Could not create vector embeddings. The PDF might be empty or corrupted."}), 500
        app.config['STATE']['vectors'] = vectors
        app.config['STATE']['pdf_filenames'] = uploaded_filenames
        return jsonify({"message": "Files uploaded and vector store ready", "uploaded_files": uploaded_filenames}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred during embedding: {str(e)}"}), 500


@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    vectors = app.config['STATE'].get('vectors')
    if not vectors:
        return jsonify({"error": "Vector store not initialized. Please upload PDF files first."}), 400

    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    start = time.process_time()
    response = retrieval_chain.invoke({'input': question})
    response_time = time.process_time() - start

    answer = response['answer']
    context_docs = response.get("context", [])

    # Format the context to be sent to the frontend
    formatted_context = []
    if context_docs:
        for doc in context_docs:
            source = doc.metadata.get("source", "Unknown").replace(f"{UPLOAD_FOLDER}/", "")
            page = doc.metadata.get("page", -1)
            formatted_context.append({"source": source, "page": page + 1})

    return jsonify({
        "answer": answer,
        "response_time": response_time,
        "context": formatted_context if formatted_context else None
    })

@app.route('/get-pdf/<path:pdf_name>', methods=['GET'])
def get_pdf(pdf_name):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_name)
    except FileNotFoundError:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/get-pdf-names', methods=['GET'])
def get_pdf_names():
    return jsonify({"pdfNames": app.config['STATE']['pdf_filenames']}), 200


# This part is for local development, Gunicorn will run the app in production
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)