/**
 * MessageList: displays all messages for the current thread.
 * Fetches messages when thread changes and renders user/assistant/tool messages distinctly.
 */

import { useEffect, useRef } from 'react';
import { User, Bot, Wrench } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { listMessages } from '@/utils/api';
import type { Message } from '@/types/api';

export function MessageList() {
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const messages = useChatStore((state) => state.messages);
  const setMessages = useChatStore((state) => state.setMessages);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingDraft = useChatStore((state) => state.streamingDraft);
  const toolDrafts = useChatStore((state) => state.toolDrafts);

  // Fetch messages when thread changes
  useEffect(() => {
    if (!currentThreadId) {
      setMessages([]);
      return;
    }

    async function loadMessages() {
      try {
        const fetchedMessages = await listMessages(currentThreadId!, 100);
        // Messages come in desc order from API; reverse for chronological display
        setMessages(fetchedMessages.reverse());
      } catch (err) {
        console.error('Failed to load messages:', err);
      }
    }
    loadMessages();
  }, [currentThreadId, setMessages]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!currentThreadId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-slate-400">
        Select a thread or create a new one to start chatting.
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-slate-400">
        No messages yet. Type below to start the conversation.
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      {messages
        .filter(msg => msg.role !== 'tool') // Hide tool messages from permanent display
        .map((msg) => (
          <MessageBubble 
            key={msg.id} 
            message={msg} 
          />
        ))}
      {/* Inline typing bubble for assistant draft */}
      {streamingDraft && streamingDraft.threadId === currentThreadId && (
        <div className="flex gap-3 items-start">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/30 dark:to-blue-800/30 flex items-center justify-center flex-shrink-0 shadow-sm">
            <Bot size={16} className="text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1 max-w-2xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
            <p className="text-sm whitespace-pre-wrap text-gray-800 dark:text-slate-200">{streamingDraft.text}</p>
          </div>
        </div>
      )}

      {/* Inline tool execution drafts (no artifacts here) */}
      {toolDrafts
        .filter((t) => t.threadId === currentThreadId)
        .map((t, idx) => (
          <div key={`tool-draft-${idx}-${t.name}`} className="flex gap-3 items-start">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-100 to-purple-200 dark:from-purple-900/30 dark:to-purple-800/30 flex items-center justify-center flex-shrink-0 shadow-sm">
              <Wrench size={16} className="text-purple-600 dark:text-purple-400 animate-spin" />
            </div>
            <div className="flex-1 bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900/10 dark:to-purple-800/10 border border-purple-200 dark:border-purple-800 rounded-xl p-4 shadow-sm">
              <div className="text-xs font-semibold text-purple-700 dark:text-purple-300 mb-1">
                {t.name}
              </div>
              {t.input && (
                <div className="text-xs text-gray-700 dark:text-slate-300">{formatParams(t.input)}</div>
              )}
            </div>
          </div>
        ))}
      
      {/* Invisible anchor for auto-scroll */}
      <div ref={messagesEndRef} />
    </div>
  );
}

/**
 * MessageBubble: renders a single message with role-specific styling.
 * Supports user, assistant, and tool messages.
 */
interface MessageBubbleProps {
  message: Message;
}

// Compact parameter formatter for tool inputs/outputs
function formatParams(value: any): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  try {
    if (Array.isArray(value)) return value.map(String).join(', ');
    if (typeof value === 'object') {
      return Object.entries(value)
        .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
        .join(' · ');
    }
    return String(value);
  } catch {
    return String(value);
  }
}

function MessageBubble({ message }: MessageBubbleProps) {
  const { role, content } = message;

  // Note: Tool messages are filtered out and not displayed in permanent chat

  // User message rendering
  if (role === 'user') {
    return (
      <div className="flex gap-3 items-start justify-end">
        <div className="flex-1 max-w-2xl bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl p-4 shadow-sm">
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {content?.text || JSON.stringify(content)}
          </p>
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/30 dark:to-blue-800/30 flex items-center justify-center flex-shrink-0 shadow-sm">
          <User size={16} className="text-blue-600 dark:text-blue-400" />
        </div>
      </div>
    );
  }

  // Assistant message rendering
  if (role === 'assistant') {
    return (
      <div className="flex gap-3 items-start">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-slate-700 dark:to-slate-600 flex items-center justify-center flex-shrink-0 shadow-sm">
          <Bot size={16} className="text-gray-600 dark:text-slate-400" />
        </div>
        <div className="flex-1 max-w-2xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
          <p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-800 dark:text-slate-200">
            {content?.text || JSON.stringify(content)}
          </p>
        </div>
      </div>
    );
  }

  // Fallback for other roles
  return (
    <div className="flex gap-3 items-start">
      <div className="flex-1 bg-gray-100 dark:bg-slate-700 rounded-lg p-3">
        <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">
          {role}
        </p>
        <p className="text-sm whitespace-pre-wrap">
          {content?.text || JSON.stringify(content)}
        </p>
      </div>
    </div>
  );
}

