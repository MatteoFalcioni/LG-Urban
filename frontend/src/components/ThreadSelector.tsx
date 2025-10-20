/**
 * ThreadSelector: Top bar for thread selection and management.
 * Shows current thread title, dropdown for switching, and controls.
 */

import { useState } from 'react';
import { ChevronDown, Plus, Sun, Moon, MessageSquare, Pencil, Archive, ArchiveRestore, Trash2 } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { createThread, updateThreadTitle, archiveThread, unarchiveThread, deleteThread } from '@/utils/api';

export function ThreadSelector() {
  const userId = useChatStore((state) => state.userId);
  const threads = useChatStore((state) => state.threads);
  const addThread = useChatStore((state) => state.addThread);
  const updateThread = useChatStore((state) => state.updateThread);
  const setThreads = useChatStore((state) => state.setThreads);
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const setCurrentThreadId = useChatStore((state) => state.setCurrentThreadId);
  const theme = useChatStore((state) => state.theme);
  const setTheme = useChatStore((state) => state.setTheme);
  const setContextUsage = useChatStore((state) => state.setContextUsage);
  const defaultConfig = useChatStore((state) => state.defaultConfig);

  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);

  const currentThread = threads.find(t => t.id === currentThreadId);
  const deletingThread = threads.find(t => t.id === deletingThreadId);

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

  // Rename thread handler
  function startEditingThread(threadId: string, currentTitle: string, e: React.MouseEvent) {
    e.stopPropagation();
    setEditingThreadId(threadId);
    setEditingTitle(currentTitle || '');
  }

  async function handleRenameThread(threadId: string) {
    if (!editingTitle.trim()) return;
    try {
      const updated = await updateThreadTitle(threadId, editingTitle.trim());
      updateThread(threadId, updated);
      setEditingThreadId(null);
    } catch (err) {
      alert('Failed to rename thread');
    }
  }

  // Archive/Unarchive thread handler
  async function handleToggleArchive(threadId: string, isArchived: boolean, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const updated = isArchived ? await unarchiveThread(threadId) : await archiveThread(threadId);
      updateThread(threadId, updated);
    } catch (err) {
      alert('Failed to archive/unarchive thread');
    }
  }

  // Delete thread handler - shows confirmation modal
  function showDeleteConfirmation(threadId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setDeletingThreadId(threadId);
  }

  async function confirmDeleteThread() {
    if (!deletingThreadId) return;
    try {
      await deleteThread(deletingThreadId);
      setThreads(threads.filter(t => t.id !== deletingThreadId));
      if (currentThreadId === deletingThreadId) {
        setCurrentThreadId(null);
      }
      setDeletingThreadId(null);
    } catch (err) {
      alert('Failed to delete thread');
      setDeletingThreadId(null);
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
                <div
                  key={thread.id}
                  className={`group relative px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all duration-200 ${
                    thread.id === currentThreadId ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' : ''
                  }`}
                >
                  {editingThreadId === thread.id ? (
                    // Edit mode
                    <div className="flex items-center gap-2">
                      <MessageSquare size={16} className="text-gray-400 dark:text-slate-500 flex-shrink-0" />
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleRenameThread(thread.id);
                          } else if (e.key === 'Escape') {
                            setEditingThreadId(null);
                          }
                        }}
                        onBlur={() => handleRenameThread(thread.id)}
                        autoFocus
                        className="flex-1 px-2 py-1 text-sm border border-blue-500 rounded bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 focus:outline-none"
                      />
                    </div>
                  ) : (
                    // Normal mode
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSelectThread(thread.id)}
                        className="flex-1 flex items-center gap-3 min-w-0"
                      >
                        <MessageSquare size={16} className="text-gray-400 dark:text-slate-500 flex-shrink-0" />
                        <span className="truncate text-sm font-medium text-gray-800 dark:text-slate-200">
                          {thread.title || 'Untitled'}
                        </span>
                        {thread.archived_at && (
                          <span className="text-xs px-2 py-1 bg-gray-200 dark:bg-slate-700 rounded-full flex-shrink-0">
                            Archived
                          </span>
                        )}
                      </button>
                      
                      {/* Action buttons - show on hover */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => startEditingThread(thread.id, thread.title || '', e)}
                          className="p-1 hover:bg-gray-200 dark:hover:bg-slate-600 rounded transition-colors"
                          title="Rename"
                        >
                          <Pencil size={14} className="text-gray-500 dark:text-slate-400" />
                        </button>
                        <button
                          onClick={(e) => handleToggleArchive(thread.id, !!thread.archived_at, e)}
                          className="p-1 hover:bg-gray-200 dark:hover:bg-slate-600 rounded transition-colors"
                          title={thread.archived_at ? 'Unarchive' : 'Archive'}
                        >
                          {thread.archived_at ? (
                            <ArchiveRestore size={14} className="text-gray-500 dark:text-slate-400" />
                          ) : (
                            <Archive size={14} className="text-gray-500 dark:text-slate-400" />
                          )}
                        </button>
                        <button
                          onClick={(e) => showDeleteConfirmation(thread.id, e)}
                          className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} className="text-red-500 dark:text-red-400" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
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

      {/* Delete Confirmation Modal */}
      {deletingThreadId && (
        <>
          <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center" onClick={() => setDeletingThreadId(null)}>
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6" onClick={(e) => e.stopPropagation()}>
              {/* Header */}
              <div className="flex items-start gap-4 mb-4">
                <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-full">
                  <Trash2 size={24} className="text-red-600 dark:text-red-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-1">
                    Delete Thread
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-slate-400">
                    Are you sure you want to delete "{deletingThread?.title || 'Untitled'}"?
                  </p>
                </div>
              </div>

              {/* Warning message */}
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-6">
                <p className="text-sm text-red-800 dark:text-red-300">
                  This action cannot be undone. All messages and data in this thread will be permanently deleted.
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setDeletingThreadId(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeleteThread}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors shadow-sm"
                >
                  Delete Thread
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}


