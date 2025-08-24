// pdf-upload/src/App.js
import React, { useState, useEffect } from 'react'; // Import useEffect
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import FileUpload from './FileUpload';
import Chatbot from './Chatbot';
import './Theme.css';

function App() {
  const [uploadComplete, setUploadComplete] = useState(false);
  
  // --- START: THEME LOGIC ---
  // 1. State to hold the current theme ('light' or 'dark')
  const [theme, setTheme] = useState('dark'); // Default theme is dark

  // 2. Effect to apply the theme class to the <html> element
  useEffect(() => {
    // Clear any existing theme classes
    document.documentElement.className = '';
    // Add the current theme's class (e.g., 'dark-mode')
    document.documentElement.classList.add(theme + '-mode');
  }, [theme]); // This code runs every time the 'theme' state changes

  // 3. Function to toggle the theme
  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'light' ? 'dark' : 'light'));
  };
  // --- END: THEME LOGIC ---

  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Pass theme and toggleTheme to the FileUpload component */}
          <Route 
            path="/" 
            element={
              <FileUpload 
                setUploadComplete={setUploadComplete} 
                theme={theme} 
                toggleTheme={toggleTheme} 
              />
            } 
          />
          {/* Pass theme and toggleTheme to the Chatbot component */}
          <Route 
            path="/chat" 
            element={
              uploadComplete ? (
                <Chatbot theme={theme} toggleTheme={toggleTheme} />
              ) : (
                <FileUpload 
                  setUploadComplete={setUploadComplete} 
                  theme={theme} 
                  toggleTheme={toggleTheme} 
                />
              )
            } 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
