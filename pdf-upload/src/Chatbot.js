import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Document, Page } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './chat.css';
import { pdfjs } from 'react-pdf';

// Set up the PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

// Style for the button that looks like a link for better accessibility
const citationButtonStyle = {
  background: 'none',
  border: 'none',
  padding: 0,
  color: '#e53935', // Use a theme color to look like a link
  textDecoration: 'underline',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 'inherit'
};

function Chatbot() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [pdfFile, setPdfFile] = useState('');
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfNames, setPdfNames] = useState([]);
  const [selectedPdf, setSelectedPdf] = useState('');
  const [isLoadingPdf, setIsLoadingPdf] = useState(true); // Added for better UX

  // Fetch the list of available PDFs when the component first loads
  useEffect(() => {
    const fetchPdfNames = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/get-pdf-names`);
        const names = response.data.pdfNames;
        setPdfNames(names);

        // **IMPROVEMENT:** Automatically load the first PDF in the list
        if (names && names.length > 0) {
          const firstPdf = names[0];
          setSelectedPdf(firstPdf);
          fetchPdf(firstPdf);
        } else {
          setIsLoadingPdf(false); // Stop loading if there are no PDFs
        }
      } catch (error) {
        console.error('Error fetching PDF names', error);
        setIsLoadingPdf(false);
      }
    };
    fetchPdfNames();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // The empty array ensures this runs only once on mount

  // Fetches a specific PDF file from the backend
  const fetchPdf = async (pdfName) => {
    setIsLoadingPdf(true);
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/get-pdf/${pdfName}`, { responseType: 'blob' });
      setPdfFile(URL.createObjectURL(response.data));
    } catch (error) {
      console.error('Error fetching PDF', error);
    } finally {
      setIsLoadingPdf(false);
    }
  };

  // Handles changing the PDF from the dropdown menu
  const handlePdfChange = (event) => {
    const pdfName = event.target.value;
    setSelectedPdf(pdfName);
    fetchPdf(pdfName);
    setPageNumber(1); // Reset to the first page when changing PDFs
  };

  // Handles clicking on a source citation in the chat
  const handleClickCitation = (pdfName, page) => {
    setSelectedPdf(pdfName);
    fetchPdf(pdfName);
    setPageNumber(page);
  };

  // Callback for when the PDF document is successfully loaded
  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  // Handlers for PDF page navigation
  const changePage = (offset) => setPageNumber(prev => prev + offset);
  const previousPage = () => changePage(-1);
  const nextPage = () => changePage(1);

  const handlePageNumberChange = (event) => {
    const newPageNumber = parseInt(event.target.value, 10);
    if (newPageNumber > 0 && newPageNumber <= numPages) {
      setPageNumber(newPageNumber);
    }
  };

  // Handles submitting a question to the backend
  const onQuestionSubmit = async () => {
    if (!question.trim()) return; // Avoid sending empty questions

    const userMessage = { sender: 'user', text: question };
    // **BUG FIX:** Use a callback function to safely update state based on the previous state
    setChatHistory(prevChat => [...prevChat, userMessage]);
    setQuestion(''); // Clear input immediately

    try {
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/ask`, { question });
      const botMessage = {
        sender: 'bot',
        text: response.data.answer,
        context: response.data.context || null,
      };
      setChatHistory(prevChat => [...prevChat, botMessage]);
    } catch (error) {
      const errorMessage = error.response ? error.response.data.error : 'An error occurred.';
      const botMessage = { sender: 'bot', text: errorMessage };
      setChatHistory(prevChat => [...prevChat, botMessage]);
    }
  };

  // Allows submitting the question by pressing Enter
  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      onQuestionSubmit();
    }
  };

  return (
    <div className="Chatbot">
      <div className="navbar">
        <div className="logo">PDFChat</div>
        <div className="profile-symbol">Profile</div>
      </div>
      <div className="main-content">
        <div className="pdf-viewer">
          <div className="pdf-viewer-header">
            <input type="number" value={pageNumber} onChange={handlePageNumberChange} min="1" max={numPages || 1} />
            <span> / {numPages || '--'}</span>
            <span className='pdf-title'>PDF Name: {selectedPdf}</span>
            <select onChange={handlePdfChange} value={selectedPdf}>
              <option value="" disabled>Select a PDF</option>
              {pdfNames.map((pdfName, index) => (
                <option key={index} value={pdfName}>{pdfName}</option>
              ))}
            </select>
          </div>
          {isLoadingPdf ? (
            <p>Loading PDF...</p>
          ) : pdfFile ? (
            <>
              <Document file={pdfFile} onLoadSuccess={onDocumentLoadSuccess}>
                <Page pageNumber={pageNumber} />
              </Document>
              <div>
                <p>Page {pageNumber} of {numPages}</p>
                <button type="button" disabled={pageNumber <= 1} onClick={previousPage}>Previous</button>
                <button type="button" disabled={pageNumber >= numPages} onClick={nextPage}>Next</button>
              </div>
            </>
          ) : (
            <p>No PDF selected or available.</p>
          )}
        </div>
        <div className="chat-container">
          <div className="chat-window">
            {chatHistory.map((msg, index) => (
              <div key={index} className={`chat-message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}>
                <p>{msg.text}</p>
                {msg.sender === 'bot' && msg.context && (
                  <div className="context">
                    {msg.context.map((doc, idx) => (
                      <p key={idx}>
                        {/* **LINTING FIX:** Replaced <a> with a styled <button> for accessibility */}
                        <button onClick={() => handleClickCitation(doc.source, doc.page)} style={citationButtonStyle}>
                          Source: {doc.source}, Page: {doc.page}
                        </button>
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="input-container">
            <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question" onKeyDown={handleKeyDown} />
            <button onClick={onQuestionSubmit}>Submit Question</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;
