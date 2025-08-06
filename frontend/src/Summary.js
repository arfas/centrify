import React from 'react';

const WordCloud = window.ReactWordcloud;

function Summary({ summary, uiSummary, loading, words, timestamp, escapeHTML }) {
  if (loading) {
    return (
      <div className="flex justify-center items-center mt-4">
        <div className="loader ease-linear rounded-full border-8 border-t-8 border-gray-200 h-12 w-12"></div>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <>
      {uiSummary && (
        <div className="p-4 bg-blue-100 dark:bg-blue-900 rounded-lg mb-4">
          <p className="text-center" dangerouslySetInnerHTML={{ __html: escapeHTML(uiSummary) }}></p>
        </div>
      )}
      <div className="mt-4 p-4 bg-gray-200 dark:bg-gray-700 rounded-lg">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-xl font-bold">Summary</h2>
          {timestamp && <span className="text-sm text-gray-500 dark:text-gray-400">{new Date(timestamp * 1000).toLocaleString()}</span>}
        </div>
        <p dangerouslySetInnerHTML={{ __html: escapeHTML(summary) }}></p>
        {WordCloud && (
          <div style={{ height: 300, width: '100%' }}>
            <WordCloud words={words} />
          </div>
        )}
      </div>
    </>
  );
}

export default Summary;
