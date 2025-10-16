/**
 * MessageInput: text input for sending messages with SSE streaming support.
 * Handles user input, sends to backend, streams assistant response, and updates UI.
 */

import { useState, useRef } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { useSSE } from '@/hooks/useSSE';
import { createThread, updateThreadConfig } from '@/utils/api';
import type { Message } from '@/types/api';

export function MessageInput() {
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const setCurrentThreadId = useChatStore((state) => state.setCurrentThreadId);
  const addMessage = useChatStore((state) => state.addMessage);
  const addThread = useChatStore((state) => state.addThread);
  const userId = useChatStore((state) => state.userId);
  const defaultConfig = useChatStore((state) => state.defaultConfig);
  const setDraft = useChatStore((state) => state.setStreamingDraft);
  const clearDraft = useChatStore((state) => state.clearStreamingDraft);
  const threads = useChatStore((state) => state.threads);
  const setThreads = useChatStore((state) => state.setThreads);
  const setContextUsage = useChatStore((state) => state.setContextUsage);
  const setIsSummarizing = useChatStore((state) => state.setIsSummarizing);
  
  const [input, setInput] = useState('');
  const streamingRef = useRef(''); // Accumulate streaming tokens (mirror to avoid stale closure on onDone)
  const addToolDraft = useChatStore((state) => state.addToolDraft);
  const updateToolDraft = useChatStore((state) => state.updateToolDraft);
  const removeToolDraft = useChatStore((state) => state.removeToolDraft);
  
  // SSE hook with handlers for streaming events
  const { sendMessage, isStreaming } = useSSE({
    onToken: (content) => {
      // Accumulate token chunks for assistant message
      streamingRef.current = streamingRef.current + content;
      if (currentThreadId) setDraft(currentThreadId, streamingRef.current);
    },
    onToolStart: (name, input) => {
      console.log(`Tool started: ${name}`, input);
      if (currentThreadId) addToolDraft(currentThreadId, name, input);
    },
    onToolEnd: (name, output, artifacts) => {
      console.log(`Tool finished: ${name}`, output, artifacts);
      if (currentThreadId) {
        // If artifacts were generated, keep them visible permanently
        if (artifacts && artifacts.length > 0) {
          updateToolDraft(currentThreadId, name, { artifacts });
          // Don't remove - artifacts stay visible
        } else {
          // No artifacts, remove the tool indicator
          removeToolDraft(currentThreadId, name);
        }
      }
    },
    onTitleUpdated: (title) => {
      // Update thread title in sidebar when auto-title completes
      if (currentThreadId) {
        setThreads(threads.map((t) => (t.id === currentThreadId ? { ...t, title } : t)));
      }
    },
    onContextUpdate: (tokensUsed, maxTokens) => {
      // Update context usage circle
      setContextUsage(tokensUsed, maxTokens);
    },
    onSummarizing: (status) => {
      // Show/hide summarization animation
      setIsSummarizing(status === 'start');
    },
    onDone: (messageId) => {
      // Stream complete; add finalized assistant message to state
      const finalText = streamingRef.current.trim();
      if (finalText) {
        const assistantMsg: Message = {
          id: messageId || crypto.randomUUID(),
          thread_id: currentThreadId!,
          role: 'assistant',
          content: { text: finalText },
        };
        addMessage(assistantMsg);
      }
      // Reset streaming state
      streamingRef.current = '';
      clearDraft();
    },
    onError: (error) => {
      console.error('Stream error:', error);
      alert(`Error: ${error}`);
      streamingRef.current = '';
      clearDraft();
    },
  });

  /**
   * Send message on Enter (Shift+Enter for new line).
   */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    
    if (!input.trim() || isStreaming) return;

    const userText = input.trim();
    setInput('');

    // If no thread selected, create one on the fly and select it
    let threadId = currentThreadId;
    if (!threadId) {
      try {
        const newThread = await createThread(userId, 'New chat');
        addThread(newThread);
        setCurrentThreadId(newThread.id);
        threadId = newThread.id;

        // Apply default config to new thread if any config is set
        if (defaultConfig.model || defaultConfig.temperature !== null || defaultConfig.system_prompt || defaultConfig.context_window !== null) {
          await updateThreadConfig(threadId, defaultConfig);
        }
      } catch (err) {
        alert('Failed to create thread');
        return;
      }
    }

    // Add user message to UI immediately (optimistic)
    const userMessageId = crypto.randomUUID();
    const userMsg: Message = {
      id: userMessageId,
      thread_id: threadId!,
      role: 'user',
      content: { text: userText },
    };
    addMessage(userMsg);

    // Send to backend and stream response
    await sendMessage(threadId!, userMessageId, { text: userText });
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 dark:border-slate-700 p-4">
      <div className="flex gap-2 items-end">
        {/* Text input */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            // Submit on Enter (not Shift+Enter)
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e as any);
            }
          }}
          placeholder={'Type a message...'}
          rows={1}
          disabled={isStreaming}
          className="flex-1 px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none disabled:opacity-50"
        />

        {/* Send button */}
        <button
          type="submit"
          disabled={!input.trim() || !currentThreadId || isStreaming}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-slate-700 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          {isStreaming ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        </button>
      </div>

      {/* Inline typing now handled in MessageList; no bottom preview */}

      {/* Active tool indicators are now rendered inline in the chat list */}
    </form>
  );
}

