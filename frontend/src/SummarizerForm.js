import React from 'react';
import Select from 'react-select';

const promptTemplates = [
  { value: 'basic', label: 'Basic Summary' },
  { value: 'sentiment', label: 'Sentiment Analysis' },
  { value: 'comparative', label: 'Comparative Summary' },
  { value: 'daily', label: 'Daily Digest' },
  { value: 'executive', label: 'Executive-Level Summary' },
  { value: 'ui', label: 'Customized for UI Display' },
];

function SummarizerForm({
  topic,
  setTopic,
  trendingTopics,
  promptTemplate,
  setPromptTemplate,
  summaryFormat,
  setSummaryFormat,
  sentimentAnalysis,
  setSentimentAnalysis,
  summaryLength,
  setSummaryLength,
  handleSubmit,
  loading,
}) {
  return (
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
      <div className="mb-4">
        <label htmlFor="prompt" className="block text-gray-700 dark:text-gray-300 font-bold mb-2">
          Prompt Template
        </label>
        <Select
          id="prompt"
          value={promptTemplate}
          onChange={setPromptTemplate}
          options={promptTemplates}
          className="text-gray-900"
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
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <input
            id="short"
            type="radio"
            name="length"
            value="short"
            checked={summaryLength === 'short'}
            onChange={(e) => setSummaryLength(e.target.value)}
            className="mr-2"
          />
          <label htmlFor="short">Short</label>
        </div>
        <div className="flex items-center">
          <input
            id="medium"
            type="radio"
            name="length"
            value="medium"
            checked={summaryLength === 'medium'}
            onChange={(e) => setSummaryLength(e.target.value)}
            className="mr-2"
          />
          <label htmlFor="medium">Medium</label>
        </div>
        <div className="flex items-center">
          <input
            id="long"
            type="radio"
            name="length"
            value="long"
            checked={summaryLength === 'long'}
            onChange={(e) => setSummaryLength(e.target.value)}
            className="mr-2"
          />
          <label htmlFor="long">Long</label>
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
  );
}

export default SummarizerForm;
