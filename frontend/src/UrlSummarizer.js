import React, { useState } from 'react';

function UrlSummarizer({ setSummary, setUiSummary, setPosts, setLoading, setError, setTimestamp }) {
  const [input, setInput] = useState('');
  const [inputType, setInputType] = useState('url');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) {
      setError('Please enter a valid URL or text.');
      return;
    }
    setError('');
    setLoading(true);
    setSummary('');
    setUiSummary('');
    setPosts([]);
    setTimestamp(null);

    const endpoint = inputType === 'url' ? '/summarize-url' : '/summarize-text';
    const payload = inputType === 'url' ? { url: input.trim() } : { text: input.trim() };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (response.ok && data.summary?.trim()) {
        setSummary(data.summary);
        setUiSummary(data.ui_summary);
        setPosts(data.posts);
        setTimestamp(data.timestamp);
      } else {
        setError(`No summary found for this ${inputType}.`);
      }
    } catch (error) {
      console.error(`Error fetching ${inputType} summary:`, error);
      setError(`Failed to generate ${inputType} summary.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-4">
      <h2 className="text-xl font-bold mb-2">Summarize URL or Text</h2>
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <input
              id="url"
              type="radio"
              name="inputType"
              value="url"
              checked={inputType === 'url'}
              onChange={(e) => setInputType(e.target.value)}
              className="mr-2"
            />
            <label htmlFor="url">URL</label>
          </div>
          <div className="flex items-center">
            <input
              id="text"
              type="radio"
              name="inputType"
              value="text"
              checked={inputType === 'text'}
              onChange={(e) => setInputType(e.target.value)}
              className="mr-2"
            />
            <label htmlFor="text">Text</label>
          </div>
        </div>
        <div className="mb-4">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
            rows="4"
            placeholder={inputType === 'url' ? 'Enter URL...' : 'Enter text...'}
          ></textarea>
        </div>
        <button
          type="submit"
          className="w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600"
        >
          Summarize
        </button>
      </form>
    </div>
  );
}

export default UrlSummarizer;
