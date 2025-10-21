/**
 * ThreadSidebar: displays list of threads, allows creating and selecting threads.
 * Fetches threads on mount and updates when new threads are created.
 */

import { useEffect, useState } from 'react';
import { Plus, MessageCircle, Sun, Moon, Trash2, Archive, Edit2, CheckSquare, Square } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { createThread, listThreads, archiveThread, unarchiveThread, deleteThread, updateThreadTitle, getThreadState } from '@/utils/api';
import type { Thread } from '@/types/api';
import { AnimatedTitle } from './AnimatedTitle';

export function ThreadSidebar() {
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
  const addToast = useChatStore((state) => state.addToast);

  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  
  // Bulk selection state
  const selectedThreadIds = useChatStore((state) => state.selectedThreadIds);
  const toggleThreadSelection = useChatStore((state) => state.toggleThreadSelection);
  const selectAllThreads = useChatStore((state) => state.selectAllThreads);
  const clearThreadSelection = useChatStore((state) => state.clearThreadSelection);
  const [showBulkActions, setShowBulkActions] = useState(false);

  /**
   * Toggle between light and dark themes only
   */
  function toggleTheme() {
    if (theme === 'light') setTheme('dark');
    else setTheme('light');
  }

  // Fetch threads on mount and when showArchived changes
  useEffect(() => {
    async function loadThreads() {
      try {
        const fetchedThreads = await listThreads(userId, 50, showArchived);
        setThreads(fetchedThreads);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load threads');
      }
    }
    loadThreads();
  }, [userId, setThreads, showArchived]);

  // Create new thread handler
  async function handleCreateThread() {
    setIsCreating(true);
    setError(null);
    try {
      const newThread = await createThread(userId, 'New chat');
      addThread(newThread);
      // Auto-select the new thread
      setCurrentThreadId(newThread.id);
      // Reset context usage for new thread (starts at 0)
      setContextUsage(0, defaultConfig.context_window ?? 30000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create thread');
    } finally {
      setIsCreating(false);
    }
  }

  // Toggle select all
  function handleSelectAll() {
    if (selectedThreadIds.size === threads.length) {
      clearThreadSelection();
    } else {
      selectAllThreads(threads.map((t) => t.id));
    }
  }

  // Bulk delete selected threads
  async function handleBulkDelete() {
    if (!confirm(`Delete ${selectedThreadIds.size} thread(s)? This cannot be undone.`)) return;

    try {
      await Promise.all(Array.from(selectedThreadIds).map((id) => deleteThread(id)));
      // Remove deleted threads from list
      setThreads(threads.filter((t) => !selectedThreadIds.has(t.id)));
      // Clear current thread if it was deleted
      if (currentThreadId && selectedThreadIds.has(currentThreadId)) {
        setCurrentThreadId(null);
      }
      clearThreadSelection();
      setShowBulkActions(false);
    } catch (err) {
      addToast('error', 'Failed to delete some threads', 'Please try again.');
    }
  }

  // Bulk archive selected threads
  async function handleBulkArchive() {
    try {
      await Promise.all(Array.from(selectedThreadIds).map((id) => archiveThread(id)));
      // Remove archived threads from list (unless showing archived)
      if (!showArchived) {
        setThreads(threads.filter((t) => !selectedThreadIds.has(t.id)));
      }
      // Clear current thread if it was archived
      if (currentThreadId && selectedThreadIds.has(currentThreadId)) {
        setCurrentThreadId(null);
      }
      clearThreadSelection();
      setShowBulkActions(false);
    } catch (err) {
      alert('Failed to archive some threads');
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with title and theme toggle */}
      <div className="p-4 border-b border-gray-200 dark:border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-semibold">Chats</h1>
          <button
            onClick={toggleTheme}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title={`Theme: ${theme}`}
          >
            {theme === 'dark' ? (
              <Moon size={16} className="text-gray-600 dark:text-slate-400" />
            ) : (
              <Sun size={16} className="text-gray-600 dark:text-slate-400" />
            )}
          </button>
        </div>
        
        <button
          onClick={handleCreateThread}
          disabled={isCreating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-400 dark:bg-slate-700 dark:hover:bg-slate-600 text-white rounded-lg transition-colors"
        >
          <Plus size={18} />
          <span>{isCreating ? 'Creating...' : 'New Thread'}</span>
        </button>

        {/* Bulk actions toggle and controls */}
        <div className="flex items-center justify-between gap-2 mt-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
              className="rounded border-gray-300 dark:border-slate-600"
            />
            <span className="text-gray-700 dark:text-slate-300">Archived</span>
          </label>
          
          <button
            onClick={() => {
              setShowBulkActions(!showBulkActions);
              if (showBulkActions) clearThreadSelection();
            }}
            className="text-xs px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-600 dark:text-slate-400 transition-colors"
          >
            {showBulkActions ? 'Cancel' : 'Select'}
          </button>
        </div>

        {/* Bulk action buttons */}
        {showBulkActions && selectedThreadIds.size > 0 && (
          <div className="mt-2 space-y-2">
            <div className="text-xs text-gray-600 dark:text-slate-400 text-center">
              {selectedThreadIds.size} selected
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleBulkArchive}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 text-white rounded text-xs transition-colors"
              >
                <Archive size={14} />
                Archive
              </button>
              <button
                onClick={handleBulkDelete}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs transition-colors"
              >
                <Trash2 size={14} />
                Delete
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="mx-4 mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto">
        {threads.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-slate-400 text-sm">
            No threads yet. Create one to start chatting!
          </div>
        ) : (
          <div className="py-2">
            {/* Select All header (only shown in bulk mode) */}
            {showBulkActions && (
              <div className="px-4 py-2 flex items-center gap-2 border-b border-gray-200 dark:border-slate-700">
                <button
                  onClick={handleSelectAll}
                  className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-slate-200"
                >
                  {selectedThreadIds.size === threads.length ? (
                    <CheckSquare size={16} className="text-gray-600 dark:text-slate-400" />
                  ) : (
                    <Square size={16} />
                  )}
                  <span>Select All</span>
                </button>
              </div>
            )}
            
            {threads.map((thread) => (
              <ThreadItem
                key={thread.id}
                thread={thread}
                isActive={thread.id === currentThreadId}
                isSelected={selectedThreadIds.has(thread.id)}
                showCheckbox={showBulkActions}
                onToggleSelect={() => toggleThreadSelection(thread.id)}
                onClick={async () => {
                  if (showBulkActions) {
                    toggleThreadSelection(thread.id);
                  } else {
                    setCurrentThreadId(thread.id);
                    // Fetch actual context usage from LangGraph state
                    try {
                      const state = await getThreadState(thread.id);
                      setContextUsage(state.token_count, state.context_window);
                    } catch (err) {
                      console.error('Failed to fetch thread state:', err);
                      // Fallback to default if fetch fails
                      setContextUsage(0, defaultConfig.context_window ?? 30000);
                    }
                  }
                }}
                addToast={addToast}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ThreadItem: individual thread entry in the sidebar.
 * Shows title, highlights if active, handles click to select.
 */
interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  isSelected: boolean;
  showCheckbox: boolean;
  onToggleSelect: () => void;
  onClick: () => void;
  addToast: (type: 'error' | 'success' | 'warning' | 'info', title: string, message?: string, duration?: number) => void;
}

function ThreadItem({ thread, isActive, isSelected, showCheckbox, onToggleSelect, onClick, addToast }: ThreadItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(thread.title || '');
  const setThreads = useChatStore((s) => s.setThreads);
  const threads = useChatStore((s) => s.threads);

  async function handleSaveTitle() {
    if (!editTitle.trim()) {
      setEditTitle(thread.title || '');
      setIsEditing(false);
      return;
    }
    try {
      await updateThreadTitle(thread.id, editTitle);
      // Update in local state
      setThreads(threads.map((t) => (t.id === thread.id ? { ...t, title: editTitle } : t)));
      setIsEditing(false);
    } catch (err) {
      addToast('error', 'Failed to update title', 'Please try again.');
      setEditTitle(thread.title || '');
      setIsEditing(false);
    }
  }

  const isArchived = !!thread.archived_at;

  return (
    <div
      className={`group w-full px-2 py-2 transition-colors ${
        isArchived ? 'opacity-60' : ''
      } ${
        isActive 
          ? 'bg-slate-100 dark:bg-slate-700 border-l-4 border-slate-600 dark:border-slate-400' 
          : isSelected
          ? 'bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-500 dark:border-yellow-400'
          : 'hover:bg-gray-50 dark:hover:bg-slate-700/50 border-l-4 border-transparent'
      }`}
    >
      <div className="flex items-center gap-2">
        {/* Checkbox for bulk selection */}
        {showCheckbox && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleSelect();
            }}
            className="flex-shrink-0"
          >
            {isSelected ? (
              <CheckSquare size={18} className="text-slate-600 dark:text-slate-400" />
            ) : (
              <Square size={18} className="text-gray-400 dark:text-slate-500" />
            )}
          </button>
        )}
        
        <button onClick={onClick} className="flex items-center gap-3 flex-1 text-left min-w-0">
          <MessageCircle size={18} className="flex-shrink-0 text-gray-400 dark:text-slate-500" />
          {isEditing ? (
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={handleSaveTitle}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveTitle();
                if (e.key === 'Escape') {
                  setEditTitle(thread.title || '');
                  setIsEditing(false);
                }
              }}
              autoFocus
              onClick={(e) => e.stopPropagation()}
              className="flex-1 px-2 py-1 text-sm font-medium border border-blue-500 rounded bg-white dark:bg-slate-900 focus:outline-none"
            />
          ) : (
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <AnimatedTitle 
                title={thread.title || 'Untitled'} 
                className="truncate text-sm font-medium"
                duration={250}
              />
              {isArchived && (
                <span className="text-xs px-1.5 py-0.5 bg-gray-200 dark:bg-slate-700 rounded flex-shrink-0">
                  Archived
                </span>
              )}
            </div>
          )}
        </button>
        {!isEditing && !showCheckbox && (
          <button
            title="Rename"
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(true);
            }}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-slate-700 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Edit2 size={14} className="text-gray-500" />
          </button>
        )}
        {!showCheckbox && <ThreadActions threadId={thread.id} isArchived={isArchived} />}
      </div>
    </div>
  );
}

function ThreadActions({ threadId, isArchived }: { threadId: string; isArchived: boolean }) {
  const setCurrentThreadId = useChatStore((s) => s.setCurrentThreadId);
  const setThreads = useChatStore((s) => s.setThreads);
  const threads = useChatStore((s) => s.threads);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  async function handleArchive(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await archiveThread(threadId);
      // Remove from list if not showing archived
      setThreads(threads.filter((t) => t.id !== threadId));
      if (useChatStore.getState().currentThreadId === threadId) setCurrentThreadId(null);
    } catch (err) {
      useChatStore.getState().addToast('error', 'Failed to archive thread', 'Please try again.');
    }
  }

  async function handleUnarchive(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const updated = await unarchiveThread(threadId);
      // Update thread in list to remove archived status
      setThreads(threads.map((t) => (t.id === threadId ? updated : t)));
    } catch (err) {
      alert('Failed to unarchive thread');
    }
  }

  async function handleDelete() {
    try {
      await deleteThread(threadId);
      setThreads(threads.filter((t) => t.id !== threadId));
      if (useChatStore.getState().currentThreadId === threadId) setCurrentThreadId(null);
      setShowDeleteConfirm(false);
    } catch (err) {
      useChatStore.getState().addToast('error', 'Failed to delete thread', 'Please try again.');
    }
  }

  return (
    <>
      <div className="flex items-center gap-1">
        {isArchived ? (
          <button
            title="Unarchive"
            onClick={handleUnarchive}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-slate-700"
          >
            <Archive size={16} className="text-green-600" />
          </button>
        ) : (
          <button
            title="Archive"
            onClick={handleArchive}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-slate-700"
          >
            <Archive size={16} className="text-gray-500" />
          </button>
        )}
        <button
          title="Delete"
          onClick={(e) => {
            e.stopPropagation();
            setShowDeleteConfirm(true);
          }}
          className="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
        >
          <Trash2 size={16} className="text-red-600" />
        </button>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <DeleteConfirmModal
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteConfirm(false)}
          threadTitle={threads.find((t) => t.id === threadId)?.title || 'Untitled'}
        />
      )}
    </>
  );
}

/**
 * DeleteConfirmModal: Modal dialog for confirming thread deletion.
 */
interface DeleteConfirmModalProps {
  onConfirm: () => void;
  onCancel: () => void;
  threadTitle: string;
}

function DeleteConfirmModal({ onConfirm, onCancel, threadTitle }: DeleteConfirmModalProps) {
  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onCancel}
    >
      <div
        className="bg-white dark:bg-slate-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold mb-2">Delete Thread?</h3>
        <p className="text-sm text-gray-600 dark:text-slate-400 mb-4">
          Are you sure you want to permanently delete <strong>"{threadTitle}"</strong>? This action
          cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

