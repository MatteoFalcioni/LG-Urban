/**
 * ThinkingBlock: Collapsible block showing Claude's extended thinking/reasoning
 * Displays with translucent styling and smooth animations
 */

import { useState } from 'react';

interface ThinkingBlockProps {
  content: string;
}

export function ThinkingBlock({ content }: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="thinking-block mb-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 w-full px-4 py-2.5 rounded-lg
                   bg-white/40 dark:bg-gray-800/40 backdrop-blur-sm
                   border border-gray-200/50 dark:border-gray-700/50
                   hover:bg-white/60 dark:hover:bg-gray-800/60
                   transition-all duration-200
                   text-left group"
      >
        {/* Brain emoji icon */}
        <span className="text-lg flex-shrink-0 animate-pulse">🧠</span>
        
        {/* "Thinking..." label */}
        <span className="text-sm font-medium text-gray-500 dark:text-gray-400 
                         opacity-70 group-hover:opacity-90 transition-opacity">
          Thinking...
        </span>
        
        {/* Expand/collapse arrow */}
        <svg
          className={`w-4 h-4 ml-auto text-gray-400 transition-transform duration-200 
                      ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Collapsible content */}
      {isExpanded && (
        <div
          className="mt-2 px-4 py-3 rounded-lg
                     bg-white/30 dark:bg-gray-800/30 backdrop-blur-sm
                     border border-gray-200/30 dark:border-gray-700/30
                     animate-fadeIn"
        >
          <p className="text-sm text-gray-600 dark:text-gray-400 
                        opacity-70 whitespace-pre-wrap leading-relaxed">
            {content}
          </p>
        </div>
      )}
    </div>
  );
}

