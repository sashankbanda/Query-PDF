import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
// import './chat.css';
import Navbar from './Navbar';

// Set up the PDF.js worker to render PDFs
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

function Chatbot({ theme, toggleTheme }) {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [pdfFile, setPdfFile] = useState('');
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfNames, setPdfNames] = useState([]);
  const [selectedPdf, setSelectedPdf] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Automatically scroll to the bottom of the chat window when new messages are added
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Fetch the list of uploaded PDF names when the component mounts
  useEffect(() => {
    const fetchPdfNames = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/get-pdf-names`);
        const names = response.data.pdfNames;
        setPdfNames(names);
        // If there are PDFs, automatically select and load the first one
        if (names.length > 0) {
          setSelectedPdf(names[0]);
          fetchPdf(names[0]);
        }
      } catch (error) {
        console.error('Error fetching PDF names:', error);
      }
    };
    fetchPdfNames();
  }, []);

  // Function to fetch a specific PDF file from the backend
  const fetchPdf = async (pdfName) => {
    if (!pdfName) return;
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/get-pdf/${pdfName}`, { responseType: 'blob' });
      const fileURL = URL.createObjectURL(response.data);
      setPdfFile(fileURL);
    } catch (error) {
      console.error('Error fetching PDF:', error);
    }
  };

  // Handle changing the selected PDF from the dropdown
  const handlePdfChange = (event) => {
    const pdfName = event.target.value;
    setSelectedPdf(pdfName);
    fetchPdf(pdfName);
    setPageNumber(1); // Reset to the first page
  };

  // Handle clicking on a citation link in the chat
  const handleClickCitation = (pdfName, page) => {
    setSelectedPdf(pdfName);
    fetchPdf(pdfName);
    setPageNumber(page);
  };

  // Callback for when the PDF document is successfully loaded
  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  // --- PDF Page Navigation ---
  const goToPreviousPage = () => {
    setPageNumber(prevPageNumber => Math.max(prevPageNumber - 1, 1));
  };

  const goToNextPage = () => {
    setPageNumber(prevPageNumber => Math.min(prevPageNumber + 1, numPages));
  };

  const handlePageNumberChange = (event) => {
    const newPageNumber = parseInt(event.target.value, 10);
    if (newPageNumber > 0 && newPageNumber <= numPages) {
      setPageNumber(newPageNumber);
    }
  };
  // --- End PDF Page Navigation ---

  // Handle submitting a question to the chatbot
  const onQuestionSubmit = async () => {
    if (!question.trim()) {
      return; // Don't submit empty questions
    }

    const userMessage = { sender: 'user', text: question };
    setChatHistory(prev => [...prev, userMessage]);
    setQuestion('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/ask`, { question });
      const botMessage = {
        sender: 'bot',
        text: response.data.answer,
        context: response.data.context || null,
      };
      setChatHistory(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = {
        sender: 'bot',
        text: error.response ? error.response.data.error : 'Sorry, an error occurred.',
      };
      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Allow submitting the question with the Enter key
  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      onQuestionSubmit();
    }
  };

  return (
    <div className="Chatbot">
      <Navbar theme={theme} toggleTheme={toggleTheme} />
      <div className="main-content">
        <div className="pdf-viewer">
          <div className="pdf-viewer-header">
            <select onChange={handlePdfChange} value={selectedPdf} className="pdf-select">
              <option value="" disabled>Select a PDF</option>
              {pdfNames.map((pdfName, index) => (
                <option key={index} value={pdfName}>{pdfName}</option>
              ))}
            </select>
          </div>
          {pdfFile ? (
            <>
              <div className="pdf-document-container">
                <Document file={pdfFile} onLoadSuccess={onDocumentLoadSuccess}>
                  <Page pageNumber={pageNumber} />
                </Document>
              </div>
              <div className="pdf-navigation">
                <button type="button" disabled={pageNumber <= 1} onClick={goToPreviousPage}>
                  Previous
                </button>
                <span>
                  Page{' '}
                  <input
                    type="number"
                    value={pageNumber}
                    onChange={handlePageNumberChange}
                    min="1"
                    max={numPages || 1}
                    className="page-input"
                  />
                  {' '}of {numPages || '--'}
                </span>
                <button type="button" disabled={pageNumber >= numPages} onClick={goToNextPage}>
                  Next
                </button>
              </div>
            </>
          ) : (
             <div className="pdf-placeholder">Select a PDF to view</div>
          )}
        </div>
        <div className="chat-container">
          <div className="chat-window">
            {chatHistory.map((msg, index) => (
              <div key={index} className={`chat-message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}>
                <p>{msg.text}</p>
                {msg.sender === 'bot' && msg.context && (
                  <div className="context">
                    <strong>Sources:</strong>
                    {msg.context.map((doc, idx) => (
                      <p key={idx} className="citation-link">
                        <a href="#" onClick={(e) => { e.preventDefault(); handleClickCitation(doc.source, doc.page); }}>
                          {doc.source}, Page: {doc.page}
                        </a>
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="chat-message bot-message">
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <div className="input-container">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about the document..."
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button onClick={onQuestionSubmit} disabled={isLoading}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;
