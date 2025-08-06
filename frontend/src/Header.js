import React from 'react';

function Header({ darkMode, setDarkMode }) {
  return (
    <div className="absolute top-4 right-4">
      <button
        onClick={() => setDarkMode(!darkMode)}
        className="p-2 rounded-full bg-gray-200 dark:bg-gray-800"
      >
        {darkMode ? '☀️' : '🌙'}
      </button>
    </div>
  );
}

export default Header;
