import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
// import './upload.css';
import Navbar from './Navbar';
import API_URL from './config';

function FileUpload({ setUploadComplete ,theme, toggleTheme }) {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const navigate = useNavigate();

  const onFileChange = (event) => {
    setFiles(Array.from(event.target.files));
    setMessage(''); // Clear any previous messages
  };

  const onFileUpload = async () => {
    if (files.length === 0) {
      setMessage('Please select files to upload');
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    setLoading(true);
    setUploadProgress(0); // Reset progress
    setMessage('Uploading...');

    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        // This function accurately tracks the upload progress
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
          if (percentCompleted === 100) {
            setMessage('Processing documents on the server...');
          } else {
            setMessage('Uploading...');
          }
        },
      });
      
      setMessage(response.data.message);
      setUploadComplete(true);
      // A small delay to show the "complete" message before navigating
      setTimeout(() => navigate('/chat'), 500);

    } catch (error) {
      let errorMessage = 'An error occurred while uploading files';
      if (error.response) {
        // Server responded with an error
        errorMessage = error.response.data.error || error.response.data.message || errorMessage;
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = 'Unable to connect to the server. Please ensure the backend is running on port 5000.';
      }
      setMessage(`Error: ${errorMessage}`);
      setUploadComplete(false);
      console.error('Upload error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="FileUpload-background">
      <Navbar theme={theme} toggleTheme={toggleTheme} />
      <div className="FileUpload">
        <h1>Upload PDF Documents</h1>
        <input type="file" onChange={onFileChange} accept="application/pdf" multiple disabled={loading} />
        <div className="file-previews">
          {files.map((file, index) => (
            <div key={index} className="file-preview">
              {file.name}
            </div>
          ))}
        </div>
        <button onClick={onFileUpload} disabled={loading || files.length === 0}>
          Upload & Start Chat
        </button>
        {message && !loading && <p>{message}</p>}
      </div>

      {/* --- This is the new Progress Bar Popup --- */}
      {loading && (
        <div className="progress-popup">
          <div className="progress-content">
            <h3>{message}</h3>
            <div className="progress">
              <div 
                className="progress-bar" 
                style={{ width: `${uploadProgress}%` }}
              >
                {uploadProgress}%
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
