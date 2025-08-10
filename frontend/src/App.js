import React, { useState, useEffect } from 'react';
import Header from './Header';
import SummarizerForm from './SummarizerForm';
import History from './History';
import Summary from './Summary';
import Posts from './Posts';
import UrlSummarizer from './UrlSummarizer';

const promptTemplates = [
  { value: 'basic', label: 'Basic Summary' },
  { value: 'sentiment', label: 'Sentiment Analysis' },
  { value: 'comparative', label: 'Comparative Summary' },
  { value: 'daily', label: 'Daily Digest' },
  { value: 'executive', label: 'Executive-Level Summary' },
  { value: 'ui', label: 'Customized for UI Display' },
];

function App() {
  const [topic, setTopic] = useState(null);
  const [summary, setSummary] = useState('');
  const [uiSummary, setUiSummary] = useState('');
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [words, setWords] = useState([]);
  const [darkMode, setDarkMode] = useState(false);
  const [history, setHistory] = useState([]);
  const [trendingTopics, setTrendingTopics] = useState([]);
  const [summaryFormat, setSummaryFormat] = useState('text');
  const [sentimentAnalysis, setSentimentAnalysis] = useState(false);
  const [summaryLength, setSummaryLength] = useState('medium');
  const [promptTemplate, setPromptTemplate] = useState(promptTemplates[0]);
  const [showUrlSummarizer, setShowUrlSummarizer] = useState(false);
  const [error, setError] = useState('');
  const [timestamp, setTimestamp] = useState(null);
  const [user, setUser] = useState(null);

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
    if (summary && window.ReactWordcloud) {
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
    if (!topic || !topic.value.trim()) {
      setError('Please enter a valid topic.');
      return;
    }
    setError('');
    setLoading(true);
    setSummary('');
    setUiSummary('');
    setPosts([]);
    setWords([]);
    setTimestamp(null);

    try {
      const response = await fetch(`/summarize?topic=${topic.value.trim()}&summary_format=${summaryFormat}&sentiment_analysis=${sentimentAnalysis}&summary_length=${summaryLength}&prompt_template=${promptTemplate.value}`);
      const data = await response.json();
      if (response.ok && data.summary?.trim()) {
        setSummary(data.summary);
        setUiSummary(data.ui_summary);
        setPosts(data.posts);
        setTimestamp(data.timestamp);
        if (topic.value.trim() && !history.includes(topic.value.trim())) {
          const newHistory = [topic.value.trim(), ...history].slice(0, 5);
          setHistory(newHistory);
          localStorage.setItem('topicHistory', JSON.stringify(newHistory));
        }
      } else {
        setError(`No summary found for topic "${topic.value.trim()}".`);
      }
    } catch (error) {
      console.error('Error fetching summary:', error);
      setError('Failed to generate summary.');
    } finally {
      setLoading(false);
    }
  };

  const handleHackerNewsSummary = async () => {
    setError('');
    setLoading(true);
    setSummary('');
    setUiSummary('');
    setPosts([]);
    setWords([]);
    setTopic(null);
    setTimestamp(null);

    try {
      const response = await fetch('/summarize-hackernews');
      const data = await response.json();
      if (response.ok && data.summary?.trim()) {
        setSummary(data.summary);
        setUiSummary(data.ui_summary);
        setPosts(data.posts);
        setTimestamp(data.timestamp);
      } else {
        setError('No summary found for Hacker News.');
      }
    } catch (error) {
      console.error('Error fetching Hacker News summary:', error);
      setError('Failed to generate Hacker News summary.');
    } finally {
      setLoading(false);
    }
  };

  const escapeHTML = (str) => {
    return str.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex items-center justify-center">
      <Header darkMode={darkMode} setDarkMode={setDarkMode} />
      <div className="max-w-md w-full bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-4">Reddit & Hacker News Summarizer</h1>
        <div className="flex justify-center mb-4">
          <a href="/auth/reddit/start" className="bg-red-500 text-white py-2 px-4 rounded-lg hover:bg-red-600">
            Connect Reddit
          </a>
        </div>
        {error && (
          <div className="p-4 bg-red-100 dark:bg-red-900 rounded-lg mb-4">
            <p className="text-center text-red-700 dark:text-red-300">{error}</p>
          </div>
        )}
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
        {showUrlSummarizer && <UrlSummarizer setSummary={setSummary} setUiSummary={setUiSummary} setPosts={setPosts} setLoading={setLoading} setError={setError} setTimestamp={setTimestamp} />}
        <SummarizerForm
          topic={topic}
          setTopic={setTopic}
          trendingTopics={trendingTopics}
          promptTemplate={promptTemplate}
          setPromptTemplate={setPromptTemplate}
          summaryFormat={summaryFormat}
          setSummaryFormat={setSummaryFormat}
          sentimentAnalysis={sentimentAnalysis}
          setSentimentAnalysis={setSentimentAnalysis}
          summaryLength={summaryLength}
          setSummaryLength={setSummaryLength}
          handleSubmit={handleSubmit}
          loading={loading}
        />
        <History history={history} setTopic={setTopic} />
        <Summary
          summary={summary}
          uiSummary={uiSummary}
          loading={loading}
          words={words}
          timestamp={timestamp}
          escapeHTML={escapeHTML}
        />
        <Posts posts={posts} loading={loading} escapeHTML={escapeHTML} />
      </div>
    </div>
  );
}

export default App;
