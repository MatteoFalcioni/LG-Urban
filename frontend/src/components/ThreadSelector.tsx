/**
 * ThreadSelector: Top bar for thread selection and management.
 * Shows current thread title, dropdown for switching, and controls.
 */

import { useState } from 'react';
import { ChevronDown, Plus, Sun, Moon, MessageSquare } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { createThread, listThreads } from '@/utils/api';
import type { Thread } from '@/types/api';

export function ThreadSelector() {
  const userId = useChatStore((state) => state.userId);
  const threads = useChatStore((state) => state.threads);
  const setThreads = useChatStore((state) => state.setThreads);
  const addThread = useChatStore((state) => state.addThread);
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const setCurrentThreadId = useChatStore((state) => state.setCurrentThreadId);
  const theme = useChatStore((state) => state.theme);
  const setTheme = useChatStore((state) => state.setTheme);
  const setContextUsage = useChatStore((state) => state.setContextUsage);
  const defaultConfig = useChatStore((state) => state.defaultConfig);

  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const currentThread = threads.find(t => t.id === currentThreadId);

  /**
   * Toggle between light and dark themes only
   */
  function toggleTheme() {
    if (theme === 'light') setTheme('dark');
    else setTheme('light');
  }

  // Create new thread handler
  async function handleCreateThread() {
    setIsCreating(true);
    try {
      const newThread = await createThread(userId, 'New chat');
      addThread(newThread);
      setCurrentThreadId(newThread.id);
      // Reset context usage for new thread
      setContextUsage(0, defaultConfig.context_window ?? 30000);
      setIsOpen(false);
    } catch (err) {
      alert('Failed to create thread');
    } finally {
      setIsCreating(false);
    }
  }

  // Select thread handler
  async function handleSelectThread(threadId: string) {
    setCurrentThreadId(threadId);
    setIsOpen(false);
    // Fetch actual context usage from LangGraph state
    try {
      const { getThreadState } = await import('@/utils/api');
      const state = await getThreadState(threadId);
      setContextUsage(state.token_count, state.context_window);
    } catch (err) {
      console.error('Failed to fetch thread state:', err);
      setContextUsage(0, defaultConfig.context_window ?? 30000);
    }
  }

  return (
    <div className="relative">
      {/* Top bar */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        {/* Thread selector */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all duration-200 min-w-0 shadow-sm hover:shadow-md"
          >
            <MessageSquare size={16} className="text-gray-600 dark:text-slate-400 flex-shrink-0" />
            <span className="truncate text-sm font-medium text-gray-800 dark:text-slate-200">
              {currentThread?.title || 'Select a thread'}
            </span>
            <ChevronDown size={14} className="text-gray-500 dark:text-slate-400 flex-shrink-0" />
          </button>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleCreateThread}
            disabled={isCreating}
            className="p-2 rounded-xl border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all duration-200 disabled:opacity-50 shadow-sm hover:shadow-md"
            title="New Thread"
          >
            <Plus size={16} className="text-gray-600 dark:text-slate-400" />
          </button>
          
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all duration-200 shadow-sm hover:shadow-md"
            title={`Theme: ${theme}`}
          >
            {theme === 'dark' ? (
              <Moon size={16} className="text-gray-600 dark:text-slate-400" />
            ) : (
              <Sun size={16} className="text-gray-600 dark:text-slate-400" />
            )}
          </button>
        </div>
      </div>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 z-50 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl shadow-lg max-h-80 overflow-y-auto">
          {threads.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-slate-400 text-sm">
              No threads yet. Create one to start chatting!
            </div>
          ) : (
            <div className="py-2">
              {threads.map((thread) => (
                <button
                  key={thread.id}
                  onClick={() => handleSelectThread(thread.id)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all duration-200 ${
                    thread.id === currentThreadId ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <MessageSquare size={16} className="text-gray-400 dark:text-slate-500 flex-shrink-0" />
                    <span className="truncate text-sm font-medium text-gray-800 dark:text-slate-200">
                      {thread.title || 'Untitled'}
                    </span>
                    {thread.archived_at && (
                      <span className="text-xs px-2 py-1 bg-gray-200 dark:bg-slate-700 rounded-full flex-shrink-0">
                        Archived
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
          
          {/* Create new thread button */}
          <div className="border-t border-gray-200 dark:border-slate-700 p-3">
            <button
              onClick={handleCreateThread}
              disabled={isCreating}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-xl transition-all duration-200 text-sm shadow-sm hover:shadow-md"
            >
              <Plus size={16} />
              <span>{isCreating ? 'Creating...' : 'New Thread'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}


