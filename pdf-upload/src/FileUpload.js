import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './upload.css';

function FileUpload({ setUploadComplete }) {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFileChange = (event) => {
    setFiles(Array.from(event.target.files));
  };

  const onFileUpload = async () => {
    if (files.length === 0) {
      setMessage('Please select files to upload');
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    setLoading(true);

    try {
      // // Find this line:
      // const response = await axios.post('http://localhost:5000/upload', formData, { ... });
      // // Change it to this:
      // const response = await axios.post(`${process.env.REACT_APP_API_URL}/upload`, formData, { ... });
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setMessage(response.data.message);
      setUploadComplete(true);
      navigate('/chat');
    } catch (error) {
      setMessage(error.response ? error.response.data.error : 'An error occurred');
      setUploadComplete(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="FileUpload-background">
      <div className="navbar">
        <div className="logo">PDFChat</div>
        <div className="profile-symbol">Profile</div>
      </div>
      <div className="FileUpload">
        <h1>Upload PDF Documents</h1>
        <input type="file" onChange={onFileChange} accept="application/pdf" multiple />
        <div className="file-previews">
          {files.map((file, index) => (
            <div key={index} className="file-preview">
              {file.name}
            </div>
          ))}
        </div>
        <button onClick={onFileUpload} disabled={loading}>
          {loading ? 'Uploading...' : 'Upload'}
        </button>
        <p>{message}</p>
      </div>
      {loading && <div className="loading-spinner">Loading...</div>}
    </div>
  );
}

export default FileUpload;
