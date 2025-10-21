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
  
  // SVG circle parameters - smaller and bolder
  const radius = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex items-center gap-2">
      {/* Circular progress ring - smaller */}
      <div className="relative w-5 h-5">
        <svg className="w-5 h-5 transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="10"
            cy="10"
            r={radius}
            stroke="var(--border)"
            strokeWidth="2.5"
            fill="none"
          />
          {/* Progress circle */}
          <circle
            cx="10"
            cy="10"
            r={radius}
            stroke="var(--user-message-bg)"
            strokeWidth="2.5"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-500"
            strokeLinecap="round"
          />
        </svg>
        {/* Center spinner when summarizing */}
        {isSummarizing && (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 size={6} className="animate-spin" style={{ color: 'var(--user-message-bg)' }} />
          </div>
        )}
      </div>

      {/* Percentage display on the side */}
      <div className="text-sm font-medium" style={{ color: 'var(--user-message-bg)' }}>
        {isSummarizing ? (
          <span className="opacity-75">Condensing...</span>
        ) : (
          <span>{Math.round(percentage)}%</span>
        )}
      </div>
    </div>
  );
}
