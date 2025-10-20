/**
 * MessageInput: text input for sending messages with SSE streaming support.
 * Handles user input, sends to backend, streams assistant response, and updates UI.
 */

import { useState, useRef } from 'react';
import { Send } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { ContextIndicator } from './ContextIndicator';
import { useSSE } from '@/hooks/useSSE';
import { createThread, updateThreadConfig, listMessages } from '@/utils/api';
import type { Message } from '@/types/api';

export function MessageInput() {
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const setCurrentThreadId = useChatStore((state) => state.setCurrentThreadId);
  const addMessage = useChatStore((state) => state.addMessage);
  const updateMessage = useChatStore((state) => state.updateMessage);
  const addThread = useChatStore((state) => state.addThread);
  const userId = useChatStore((state) => state.userId);
  const defaultConfig = useChatStore((state) => state.defaultConfig);
  const setDraft = useChatStore((state) => state.setStreamingDraft);
  const clearDraft = useChatStore((state) => state.clearStreamingDraft);
  const setThreads = useChatStore((state) => state.setThreads);
  const setContextUsage = useChatStore((state) => state.setContextUsage);
  const setIsSummarizing = useChatStore((state) => state.setIsSummarizing);
  
  const [input, setInput] = useState('');
  const streamingRef = useRef(''); // Accumulate streaming tokens (mirror to avoid stale closure on onDone)
  const addToolDraft = useChatStore((state) => state.addToolDraft);
  const removeToolDraft = useChatStore((state) => state.removeToolDraft);
  const clearToolDrafts = useChatStore((state) => state.clearToolDrafts);
  const addArtifactBubble = useChatStore((state) => state.addArtifactBubble);
  const clearArtifactBubbles = useChatStore((state) => state.clearArtifactBubbles);
  const contextUsage = useChatStore((state) => state.contextUsage);
  const isSummarizing = useChatStore((state) => state.isSummarizing);
  
  // Use context_window from defaultConfig if contextUsage.maxTokens is still default
  const effectiveMaxTokens = contextUsage.maxTokens === 30000 && defaultConfig.context_window 
    ? defaultConfig.context_window 
    : contextUsage.maxTokens;
  
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
        // Always remove tool draft when complete
        removeToolDraft(currentThreadId, name);
        
        // Show artifacts immediately during streaming
        if (artifacts && artifacts.length > 0) {
          addArtifactBubble(currentThreadId, name, artifacts);
        }
      }
    },
    onTitleUpdated: (title) => {
      // Update thread title in sidebar when auto-title completes
      if (currentThreadId) {
        // Get current threads from store to avoid stale closure
        const currentThreads = useChatStore.getState().threads;
        // Add a small delay to make the animation feel more natural
        setTimeout(() => {
          setThreads(currentThreads.map((t) => (t.id === currentThreadId ? { ...t, title } : t)));
        }, 100);
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
    onDone: async (messageId) => {
      console.log('onDone called with messageId:', messageId);
      // Stream complete; add finalized assistant message to state
      const finalText = streamingRef.current.trim();
      console.log('Final text length:', finalText.length);
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
      
      // Clear any remaining tool drafts (handles failed tools that didn't send tool_end)
      if (currentThreadId) {
        clearToolDrafts(currentThreadId);
      }
      
      // Smoothly update the assistant message with artifacts from DB
      if (currentThreadId && messageId) {
        // Short delay to ensure backend has persisted everything
        setTimeout(async () => {
          try {
            const messages = await listMessages(currentThreadId);
            // Find the assistant message we just added
            const assistantMsg = messages.find(m => m.id === messageId);
            if (assistantMsg && assistantMsg.artifacts && assistantMsg.artifacts.length > 0) {
              // Update only this specific message with artifacts
              updateMessage(messageId, { artifacts: assistantMsg.artifacts });
            }
            // Clear artifact bubbles now that artifacts are properly saved to DB
            clearArtifactBubbles(currentThreadId);
          } catch (err) {
            console.error('Failed to update message with artifacts:', err);
          }
        }, 100); // Minimal delay for DB to persist
      }
    },
    onError: (error) => {
      console.error('Stream error:', error);
      alert(`Error: ${error}`);
      streamingRef.current = '';
      clearDraft();
      
      // Clear any hanging tool drafts when stream errors out
      if (currentThreadId) {
        clearToolDrafts(currentThreadId);
      }
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
    <form onSubmit={handleSubmit} className="border-t p-4" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-primary)' }}>
      <div className="flex gap-3 items-end">
        {/* Text input with context indicator */}
        <div className="flex-1 relative">
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
            className="w-full px-4 py-3 pr-16 rounded-xl focus:outline-none focus:ring-2 focus:border-transparent resize-none disabled:opacity-50 transition-all duration-200 text-sm"
            style={{ 
              border: '1px solid var(--border)', 
              backgroundColor: 'var(--bg-secondary)', 
              color: 'var(--text-primary)'
            } as React.CSSProperties}
          />
          
          {/* Context indicator in bottom-right corner */}
          <div className="absolute bottom-3 right-3">
            <ContextIndicator 
              tokensUsed={contextUsage.tokensUsed}
              maxTokens={effectiveMaxTokens}
              isSummarizing={isSummarizing}
            />
          </div>
        </div>

        {/* Send button (hidden when streaming) */}
        {!isStreaming && (
          <button
            type="submit"
            disabled={!input.trim() || !currentThreadId}
            className="px-4 py-3 rounded-xl transition-all duration-200 flex items-center gap-2 shadow-sm hover:shadow-md disabled:shadow-none disabled:cursor-not-allowed"
            style={{ 
              backgroundColor: 'var(--user-message-bg)', 
              color: 'var(--user-message-text)',
              opacity: (!input.trim() || !currentThreadId) ? 0.5 : 1
            }}
          >
            <Send size={18} />
          </button>
        )}

      </div>

      {/* Inline typing now handled in MessageList; no bottom preview */}

      {/* Active tool indicators are now rendered inline in the chat list */}
    </form>
  );
}

