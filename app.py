import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import time
import shutil

from langchain_groq import ChatGroq
# FIX: The 'RecursiveCharacterTextSplitter' was moved to its own dedicated package 
# in the LangChain ecosystem updates. We import it directly from 'langchain_text_splitters'.
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    # Fallback to deprecated import if new package not available
    from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

app = Flask(__name__)
# Configure CORS to allow requests from React app - more permissive for development
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"])

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['VECTORS'] = None
app.config['PDF_FILENAMES'] = []

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

groq_api_key = os.getenv("GROQ_API_KEY")

# Use a supported Groq model - llama-3.1-8b-instant is fast and reliable
# Alternative models: "mixtral-8x7b-32768", "llama-3.1-70b-versatile"
llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.1-8b-instant")

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def vector_embedding(directory):
    """
    Create vector embeddings for PDF documents.
    Uses HuggingFace embeddings (free, no API key required) as a reliable alternative.
    """
    try:
        # Use HuggingFace embeddings - free and doesn't require API keys
        # Using a lightweight model that works well for document embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}  # Use CPU to avoid GPU requirements
        )
        
        loader = PyPDFDirectoryLoader(directory)
        pages = loader.load_and_split()
        
        if not pages:
            raise ValueError("No pages were extracted from the PDF files")
        
        vectors = FAISS.from_documents(pages, embeddings)
        return vectors
    except Exception as e:
        error_msg = str(e)
        # Provide more helpful error messages
        if "quota" in error_msg.lower() or "429" in error_msg:
            raise Exception("API quota exceeded. Please check your API billing or use a different embedding service.")
        elif "no pages" in error_msg.lower() or "empty" in error_msg.lower():
            raise Exception("Failed to extract text from PDF files. Please ensure the PDFs contain readable text.")
        else:
            raise Exception(f"Error creating embeddings: {error_msg}")

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
    app.config['PDF_FILENAMES'] = []

@app.route('/upload', methods=['POST'])
def upload_files():
    clear_upload_folder()
    if 'files' not in request.files:
        return jsonify({"error": "No files part"}), 400

    uploaded_files = request.files.getlist('files')
    uploaded_filenames = []

    for file in uploaded_files:
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_filenames.append(filename)
            app.config['PDF_FILENAMES'].append(filename)
        else:
            return jsonify({"error": "File type not allowed"}), 400

    # Perform vector embedding after all files are uploaded
    try:
        app.config['VECTORS'] = vector_embedding(app.config['UPLOAD_FOLDER'])
        return jsonify({"message": "Files uploaded and vector store ready", "uploaded_files": uploaded_filenames}), 200
    except Exception as e:
        # Clean up uploaded files if embedding fails
        clear_upload_folder()
        error_message = str(e)
        return jsonify({"error": f"Failed to process PDFs: {error_message}"}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        question = data.get('question')
        if not question:
            return jsonify({"error": "No question provided"}), 400

        if not app.config['VECTORS']:
            return jsonify({"error": "No vectors available. Upload a PDF first."}), 400

        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = app.config['VECTORS'].as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)
        
        start = time.process_time()
        response = retrieval_chain.invoke({'input': question})
        response_time = time.process_time() - start

        answer = response.get('answer', 'No answer generated')
        # Use .get() to safely access 'context'
        context = response.get("context") 

        # Clean up and format context sources for the client
        formatted_context = None
        if context:
            formatted_context = []
            seen_sources = set()
            uploads_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])

            for doc in context:
                metadata = doc.metadata or {}

                source_path = metadata.get("source")
                page_number = metadata.get("page", metadata.get("page_number"))

                if not source_path or page_number is None:
                    continue

                # Normalize the file path so the frontend receives a stable name
                try:
                    source_name = os.path.relpath(source_path, uploads_dir)
                except ValueError:
                    source_name = os.path.basename(source_path)

                source_name = source_name.replace("\\", "/")

                try:
                    page = int(page_number)
                except (ValueError, TypeError):
                    continue

                # Most loaders are 0-indexed; ensure we return 1-indexed pages
                page_display = page + 1 if page >= 0 else 1

                unique_key = (source_name, page_display)

                if unique_key not in seen_sources:
                    formatted_context.append({"source": source_name, "page": page_display})
                    seen_sources.add(unique_key)

        return jsonify({
            "answer": answer,
            "response_time": response_time,
            "context": formatted_context
        })
    except Exception as e:
        error_msg = str(e)
        # Provide helpful error messages
        if "model" in error_msg.lower() and "decommissioned" in error_msg.lower():
            return jsonify({"error": "The AI model has been updated. Please restart the server."}), 500
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return jsonify({"error": "API rate limit exceeded. Please try again later."}), 429
        elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
            return jsonify({"error": "API authentication failed. Please check your API keys."}), 401
        else:
            return jsonify({"error": f"Error processing question: {error_msg}"}), 500

@app.route('/get-pdf/<path:pdf_name>', methods=['GET'])
def get_pdf(pdf_name):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_name)
    if os.path.exists(pdf_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_name)
    else:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/get-pdf-names', methods=['GET'])
def get_pdf_names():
    return jsonify({"pdfNames": app.config['PDF_FILENAMES']}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
