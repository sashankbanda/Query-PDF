import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import time
import shutil
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['VECTORS'] = None
app.config['PDF_FILENAMES'] = []

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

groq_api_key = os.getenv("GROQ_API_KEY")
os.environ['GOOGLE_API_KEY'] = os.getenv("GOOGLE_API_KEY")

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

def extract_text_with_pymupdf(pdf_path):
    """Extract text using PyMuPDF (supports both text and some image PDFs)"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        print(f"PyMuPDF extraction failed: {e}")
        return ""

def extract_text_with_ocr(pdf_path):
    """Extract text from image-based PDF using OCR"""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)  # Higher DPI for better OCR
        
        full_text = ""
        for i, image in enumerate(images):
            # Preprocess image for better OCR
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Use pytesseract with optimized configuration
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?;:()[]{}@#$%^&*+-/= '
            text = pytesseract.image_to_string(image, config=custom_config)
            
            if text.strip():
                full_text += f"\n--- Page {i+1} ---\n{text}\n"
        
        return full_text.strip()
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        return ""

def process_pdf_file(pdf_path):
    """Process a PDF file with fallback from text extraction to OCR"""
    documents = []
    
    # First try: Extract text directly (works for text-based PDFs)
    direct_text = extract_text_with_pymupdf(pdf_path)
    
    if direct_text and len(direct_text) > 100:  # If we got substantial text
        print(f"Successfully extracted text directly from {os.path.basename(pdf_path)}")
        # Split the text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(direct_text)
        
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={"source": os.path.basename(pdf_path), "page": i}
            ))
    else:
        # Second try: Use OCR for image-based PDFs
        print(f"Using OCR for {os.path.basename(pdf_path)}")
        ocr_text = extract_text_with_ocr(pdf_path)
        
        if ocr_text and len(ocr_text) > 50:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,  # Smaller chunks for OCR text
                chunk_overlap=100,
                length_function=len
            )
            chunks = text_splitter.split_text(ocr_text)
            
            for i, chunk in enumerate(chunks):
                documents.append(Document(
                    page_content=chunk,
                    metadata={"source": os.path.basename(pdf_path), "page": i, "method": "OCR"}
                ))
        else:
            print(f"Warning: Could not extract meaningful text from {os.path.basename(pdf_path)}")
    
    return documents

def vector_embedding(directory):
    """Create vector embeddings from PDFs in directory"""
    print("Starting vector embedding process...")
    
    # Use free HuggingFace embeddings (no API quotas)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},  # Use CPU to avoid GPU issues
        encode_kwargs={'normalize_embeddings': True}
    )
    
    all_documents = []
    
    # Process each PDF file
    for filename in os.listdir(directory):
        if filename.endswith('.pdf'):
            filepath = os.path.join(directory, filename)
            print(f"Processing: {filename}")
            
            documents = process_pdf_file(filepath)
            if documents:
                all_documents.extend(documents)
                print(f"✓ Extracted {len(documents)} chunks from {filename}")
            else:
                print(f"✗ Failed to extract text from {filename}")
    
    if not all_documents:
        raise Exception("No text could be extracted from any PDF files")
    
    print(f"Total documents processed: {len(all_documents)}")
    
    # Create FAISS vector store
    vectors = FAISS.from_documents(all_documents, embeddings)
    print("✓ Vector store created successfully")
    
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

    try:
        # Perform vector embedding after all files are uploaded
        app.config['VECTORS'] = vector_embedding(app.config['UPLOAD_FOLDER'])
        return jsonify({
            "message": "Files uploaded and vector store ready", 
            "uploaded_files": uploaded_filenames
        }), 200
    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    if not app.config['VECTORS']:
        return jsonify({"error": "No vectors available. Upload a PDF first."}), 400

    try:
        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = app.config['VECTORS'].as_retriever(search_kwargs={"k": 4})
        retrieval_chain = create_retrieval_chain(retriever, document_chain)
        
        start = time.process_time()
        response = retrieval_chain.invoke({'input': question})
        response_time = time.process_time() - start

        answer = response['answer']
        context = response.get("context")

        # Clean up and format context sources
        formatted_context = None
        if context:
            formatted_context = []
            seen_sources = set()
            for doc in context:
                source_path = doc.metadata.get("source")
                page_number = doc.metadata.get("page")
                
                if source_path and page_number is not None:
                    source_name = source_path
                    page = int(page_number) + 1
                    
                    unique_key = (source_name, page)
                    if unique_key not in seen_sources:
                        formatted_context.append({"source": source_name, "page": page})
                        seen_sources.add(unique_key)

        return jsonify({
            "answer": answer,
            "response_time": response_time,
            "context": formatted_context
        })
    except Exception as e:
        return jsonify({"error": f"Error processing question: {str(e)}"}), 500

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