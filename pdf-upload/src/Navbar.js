// pdf-upload/src/Navbar.js

import React from 'react';

const Navbar = ({ theme, toggleTheme }) => {
  return (
    <div className="navbar">
      <div className="logo">PDFChat</div>
      
      {/* THIS IS YOUR TOGGLE BUTTON */}
      <button onClick={toggleTheme} className="theme-toggle-button">
        {theme === 'light' ? '🌙' : '☀️'}
      </button>
      
      {/* <div className="profile-symbol">Profile</div> */}
    </div>
  );
};

export default Navbar;