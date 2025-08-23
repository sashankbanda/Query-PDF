import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Document, Page } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './chat.css'
import { pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

function Chatbot() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [pdfFile, setPdfFile] = useState('');
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfNames, setPdfNames] = useState([]);
  const [dropDown, setDropDown] = useState(false)
  const [selectedPdf, setSelectedPdf] = useState('');

  useEffect(() => {
    const fetchPdfNames = async () => {
      try {
        // const response = await axios.get('http://localhost:5000/get-pdf-names');
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/get-pdf-names`);
        setPdfNames(response.data.pdfNames);
      } catch (error) {
        console.error('Error fetching PDF names', error);
      }
    };
    fetchPdfNames();
  }, []);

  const fetchPdf = async (pdfName) => {
    try {
      // const response = await axios.get(`http://localhost:5000/get-pdf/${pdfName}`, { responseType: 'blob' });
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/get-pdf/${pdfName}`, { responseType: 'blob' });
      setPdfFile(URL.createObjectURL(response.data));
    } catch (error) {
      console.error('Error fetching PDF', error);
    }
  };
  const handlePdfChange = (event) => {
    const pdfName = event.target.value;
    setDropDown(true)
    setSelectedPdf(pdfName);
    fetchPdf(pdfName);
    setPageNumber(1);
  };

  const handleClickCitation = (pdfName, page) => {
    setSelectedPdf(pdfName)
    setDropDown(false)
    fetchPdf(pdfName);
    setPageNumber(page);
  };

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  function changePage(offset) {
    setPageNumber(prevPageNumber => prevPageNumber + offset);
  }

  function previousPage() {
    changePage(-1);
  }

  function nextPage() {
    changePage(1);
  }

  const handlePageNumberChange = (event) => {
    const pageNumber = parseInt(event.target.value, 10);
    if (pageNumber > 0 && pageNumber <= numPages) {
      setPageNumber(pageNumber);
    }
  };

  const onQuestionSubmit = async () => {
    if (!question) {
      alert('Please enter a question');
      return;
    }

    const userMessage = { sender: 'user', text: question };
    setChatHistory([...chatHistory, userMessage]);

    try {
      // const response = await axios.post('http://localhost:5000/ask', { question });
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/ask`, { question });
      const botMessage = {
        sender: 'bot',
        text: response.data.answer,
        context: response.data.context || null,
      };
      setChatHistory([...chatHistory, userMessage, botMessage]);
    } catch (error) {
      const botMessage = {
        sender: 'bot',
        text: error.response ? error.response.data.error : 'An error occurred',
      };
      setChatHistory([...chatHistory, userMessage, botMessage]);
    }

    setQuestion('');
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      onQuestionSubmit();
    }
  }

  return (
    <div className="Chatbot">
      <div className="navbar">
        <div className="logo">PDFChat</div>
        <div className="profile-symbol">Profile</div>
      </div>
      <div className="main-content">
        <div className="pdf-viewer">
        <div className="pdf-viewer-header">
              <input
                type="number"
                value={pageNumber}
                onChange={handlePageNumberChange}
                min="1"
                max={numPages || 1}
              />
              <span> / {numPages || '--'}</span>
          <span className='pdf-title'>PDF Name: {selectedPdf}</span>
          <select onChange={handlePdfChange} value={selectedPdf}>
            <option value="" disabled>Select a PDF</option>
            {pdfNames.map((pdfName, index) => (
              <option key={index} value={pdfName}>{pdfName}</option>
            ))}
          </select>
        </div>
          {/* {pdfFile && dropDown && (
            <Document
            file={pdfFile}
            onLoadSuccess={onDocumentLoadSuccess}
            >
            {Array.from(
              new Array(numPages),
              (el, index) => (
                <Page
                  key={`page_${index + 1}`}
                  pageNumber={index + 1}
                />
              ),
            )}
          </Document>
          )} */}
          {pdfFile && (
            <>
            <Document
              file={pdfFile}
              onLoadSuccess={onDocumentLoadSuccess}
            >
              <Page pageNumber={pageNumber} />
            </Document>
            <div>
              <p>
                Page {pageNumber || (numPages ? 1 : '--')} of {numPages || '--'}
              </p>
              <button
                type="button"
                disabled={pageNumber <= 1}
                onClick={previousPage}
              >
                Previous
              </button>
              <button
                type="button"
                disabled={pageNumber >= numPages}
                onClick={nextPage}
              >
                Next
              </button>
            </div>

            </>
            
          )}
        </div>
        <div className="chat-container">
          <div className="chat-window">
            {chatHistory.map((msg, index) => (
              <div
                key={index}
                className={`chat-message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}
              >
                <p>{msg.text}</p>
                {msg.sender === 'bot' && msg.context && (
                  <div className="context">
                    {msg.context.map((doc, idx) => (
                      <p key={idx}>
                        <a href="#" onClick={() => handleClickCitation(doc.source, doc.page)}>
                          Source: {doc.source}, Page: {doc.page}
                        </a>
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="input-container">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question"
              onKeyDown={handleKeyDown}
            />
            <button onClick={onQuestionSubmit}>Submit Question</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;