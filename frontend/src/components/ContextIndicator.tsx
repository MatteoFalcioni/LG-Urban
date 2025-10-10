/**
 * ContextIndicator: circular progress indicator showing token usage.
 * Displays as a ring that fills as context grows, with "Summarizing..." when active.
 */

import { Loader2 } from 'lucide-react';

interface ContextIndicatorProps {
  tokensUsed: number;
  maxTokens: number;
  isSummarizing: boolean;
}

export function ContextIndicator({ tokensUsed, maxTokens, isSummarizing }: ContextIndicatorProps) {
  // Cap tokens at 90% threshold (summarization triggers at 90%)
  const effectiveMax = maxTokens * 0.9;
  const displayTokens = Math.min(tokensUsed, effectiveMax);
  
  // Calculate percentage (0-90 max, relative to maxTokens)
  const percentage = (displayTokens / maxTokens) * 100;
  
  // SVG circle parameters
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex items-center gap-2">
      {/* Circular progress ring */}
      <div className="relative w-10 h-10">
        <svg className="w-10 h-10 transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="20"
            cy="20"
            r={radius}
            stroke="currentColor"
            strokeWidth="3"
            fill="none"
            className="text-gray-200 dark:text-slate-700"
          />
          {/* Progress circle */}
          <circle
            cx="20"
            cy="20"
            r={radius}
            stroke="currentColor"
            strokeWidth="3"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`transition-all duration-500 ${
              percentage > 80 ? 'text-red-500' : percentage > 65 ? 'text-yellow-500' : 'text-blue-500'
            }`}
            strokeLinecap="round"
          />
        </svg>
        {/* Center percentage or spinner */}
        <div className="absolute inset-0 flex items-center justify-center">
          {isSummarizing ? (
            <Loader2 size={14} className="animate-spin text-purple-600" />
          ) : (
            <span className="text-xs font-semibold text-gray-700 dark:text-slate-300">
              {Math.round(percentage)}
            </span>
          )}
        </div>
      </div>

      {/* Token count label */}
      <div className="flex flex-col text-xs">
        <span className="text-gray-600 dark:text-slate-400">
          {isSummarizing ? (
            <span className="text-purple-600 dark:text-purple-400 font-semibold">Condensing...</span>
          ) : (
            <span>
              {(displayTokens / 1000).toFixed(1)}k / {(maxTokens / 1000).toFixed(0)}k
            </span>
          )}
        </span>
      </div>
    </div>
  );
}
