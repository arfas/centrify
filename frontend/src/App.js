import React, { useState, useEffect } from 'react';
import UrlSummarizer from './UrlSummarizer';

const WordCloud = window.ReactWordcloud;
const Select = window.ReactSelect;

function App() {
  const [topic, setTopic] = useState(null);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [words, setWords] = useState([]);
  const [darkMode, setDarkMode] = useState(false);
  const [history, setHistory] = useState([]);
  const [trendingTopics, setTrendingTopics] = useState([]);
  const [summaryFormat, setSummaryFormat] = useState('text');
  const [sentimentAnalysis, setSentimentAnalysis] = useState(false);
  const [showUrlSummarizer, setShowUrlSummarizer] = useState(false);

  useEffect(() => {
    const fetchTrendingTopics = async () => {
      try {
        const response = await fetch('/trending-topics');
        const data = await response.json();
        setTrendingTopics(data.map(topic => ({ value: topic, label: topic })));
      } catch (error) {
        console.error('Error fetching trending topics:', error);
      }
    };
    fetchTrendingTopics();
  }, []);

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
    if (!topic) return;
    setLoading(true);
    setSummary('');
    setWords([]);

    try {
      const response = await fetch(`/summarize?topic=${topic.value}&summary_format=${summaryFormat}&sentiment_analysis=${sentimentAnalysis}`);
      const data = await response.json();
      setSummary(data.summary);
      if (topic.value && !history.includes(topic.value)) {
        const newHistory = [topic.value, ...history].slice(0, 5);
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

  const handleHackerNewsSummary = async () => {
    setLoading(true);
    setSummary('');
    setWords([]);
    setTopic(null);

    try {
      const response = await fetch('/summarize-hackernews');
      const data = await response.json();
      setSummary(data.summary);
    } catch (error) {
      console.error('Error fetching Hacker News summary:', error);
      setSummary('Failed to generate Hacker News summary.');
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
        <h1 className="text-2xl font-bold text-center mb-4">Reddit & Hacker News Summarizer</h1>
        <div className="flex justify-center mb-4 space-x-2">
          <button
            onClick={handleHackerNewsSummary}
            className="bg-orange-500 text-white py-2 px-4 rounded-lg hover:bg-orange-600"
            disabled={loading}
          >
            Summarize Hacker News
          </button>
          <button
            onClick={() => setShowUrlSummarizer(!showUrlSummarizer)}
            className="bg-purple-500 text-white py-2 px-4 rounded-lg hover:bg-purple-600"
          >
            {showUrlSummarizer ? 'Hide' : 'Summarize URL/Text'}
          </button>
        </div>
        {showUrlSummarizer && <UrlSummarizer setSummary={setSummary} setLoading={setLoading} />}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="topic" className="block text-gray-700 dark:text-gray-300 font-bold mb-2">
              Reddit Topic
            </label>
            <Select
              id="topic"
              value={topic}
              onChange={setTopic}
              options={trendingTopics}
              className="text-gray-900"
              isClearable
              isSearchable
              placeholder="Select or type a topic..."
            />
          </div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <input
                id="bullets"
                type="radio"
                name="format"
                value="bullets"
                checked={summaryFormat === 'bullets'}
                onChange={(e) => setSummaryFormat(e.target.value)}
                className="mr-2"
              />
              <label htmlFor="bullets">Bullets</label>
            </div>
            <div className="flex items-center">
              <input
                id="tldr"
                type="radio"
                name="format"
                value="tldr"
                checked={summaryFormat === 'tldr'}
                onChange={(e) => setSummaryFormat(e.target.value)}
                className="mr-2"
              />
              <label htmlFor="tldr">TL;DR</label>
            </div>
            <div className="flex items-center">
              <input
                id="sentiment"
                type="checkbox"
                checked={sentimentAnalysis}
                onChange={(e) => setSentimentAnalysis(e.target.checked)}
                className="mr-2"
              />
              <label htmlFor="sentiment">Sentiment Analysis</label>
            </div>
          </div>
          <button
            type="submit"
            className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
            disabled={loading || !topic}
          >
            {loading ? 'Summarizing...' : 'Summarize Reddit'}
          </button>
        </form>
        {history.length > 0 && (
          <div className="mt-4">
            <h2 className="text-xl font-bold mb-2">History</h2>
            <div className="flex flex-wrap gap-2">
              {history.map((item, index) => (
                <button
                  key={index}
                  onClick={() => setTopic({ value: item, label: item })}
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
