import React, { useState, useEffect } from 'react';

const WordCloud = window.ReactWordcloud;

function App() {
  const [topic, setTopic] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [words, setWords] = useState([]);
  const [darkMode, setDarkMode] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    setDarkMode(isDarkMode);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  useEffect(() => {
    const storedHistory = JSON.parse(localStorage.getItem('topicHistory')) || [];
    setHistory(storedHistory);
  }, []);

  useEffect(() => {
    if (summary && WordCloud) {
      const wordMap = {};
      summary.split(/[ ,.\n]+/).forEach((word) => {
        if (word) {
          wordMap[word] = (wordMap[word] || 0) + 1;
        }
      });
      setWords(Object.keys(wordMap).map(key => ({ text: key, value: wordMap[key] })));
    }
  }, [summary]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSummary('');
    setWords([]);

    try {
      const response = await fetch(`/summarize?topic=${topic}`);
      const data = await response.json();
      setSummary(data.summary);
      if (topic && !history.includes(topic)) {
        const newHistory = [topic, ...history].slice(0, 5);
        setHistory(newHistory);
        localStorage.setItem('topicHistory', JSON.stringify(newHistory));
      }
    } catch (error) {
      console.error('Error fetching summary:', error);
      setSummary('Failed to generate summary.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex items-center justify-center">
      <div className="absolute top-4 right-4">
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="p-2 rounded-full bg-gray-200 dark:bg-gray-800"
        >
          {darkMode ? '☀️' : '🌙'}
        </button>
      </div>
      <div className="max-w-md w-full bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-4">Reddit Summarizer</h1>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="topic" className="block text-gray-700 dark:text-gray-300 font-bold mb-2">
              Topic
            </label>
            <input
              type="text"
              id="topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
              placeholder="e.g., python"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
            disabled={loading}
          >
            {loading ? 'Summarizing...' : 'Summarize'}
          </button>
        </form>
        {history.length > 0 && (
          <div className="mt-4">
            <h2 className="text-xl font-bold mb-2">History</h2>
            <div className="flex flex-wrap gap-2">
              {history.map((item, index) => (
                <button
                  key={index}
                  onClick={() => setTopic(item)}
                  className="bg-gray-200 dark:bg-gray-700 px-3 py-1 rounded-full"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        )}
        {loading && (
          <div className="flex justify-center items-center mt-4">
            <div className="loader ease-linear rounded-full border-8 border-t-8 border-gray-200 h-12 w-12"></div>
          </div>
        )}
        {summary && !loading && WordCloud && (
          <div className="mt-4 p-4 bg-gray-200 dark:bg-gray-700 rounded-lg">
            <h2 className="text-xl font-bold mb-2">Summary</h2>
            <p>{summary}</p>
            <div style={{ height: 300, width: '100%' }}>
              <WordCloud words={words} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
