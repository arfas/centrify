import React from 'react';

function Posts({ posts, loading, escapeHTML }) {
  if (loading || posts.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h2 className="text-xl font-bold mb-2">Posts</h2>
      <div className="space-y-4">
        {posts.map((post, index) => (
          <div key={index} className="p-4 bg-gray-200 dark:bg-gray-700 rounded-lg">
            <h3 className="font-bold">
              <a href={post.url} target="_blank" rel="noopener noreferrer" className="hover:underline" dangerouslySetInnerHTML={{ __html: escapeHTML(post.title) }}>
              </a>
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400" dangerouslySetInnerHTML={{ __html: escapeHTML(post.text) }}></p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Posts;
