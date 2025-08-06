import React from 'react';

function History({ history, setTopic }) {
  if (history.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h2 className="text-xl font-bold mb-2">Recent Topics</h2>
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
  );
}

export default History;
