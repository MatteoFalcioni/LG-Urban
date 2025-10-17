/**
 * MessageList: displays all messages for the current thread.
 * Fetches messages when thread changes and renders user/assistant/tool messages distinctly.
 */

import { useEffect, useRef } from 'react';
import { User, Bot, Wrench } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { listMessages } from '@/utils/api';
import type { Message } from '@/types/api';
import { ArtifactGrid } from './ArtifactCard';

export function MessageList() {
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const messages = useChatStore((state) => state.messages);
  const setMessages = useChatStore((state) => state.setMessages);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingDraft = useChatStore((state) => state.streamingDraft);
  const toolDrafts = useChatStore((state) => state.toolDrafts);
  const artifactBubbles = useChatStore((state) => state.artifactBubbles);

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
    <div className="space-y-4">
      {messages.map((msg, idx) => {
        // For assistant messages, check if the previous message was a tool with artifacts
        let toolArtifacts: typeof msg.artifacts = undefined;
        if (msg.role === 'assistant' && idx > 0) {
          const prevMsg = messages[idx - 1];
          if (prevMsg.role === 'tool' && prevMsg.artifacts && prevMsg.artifacts.length > 0) {
            toolArtifacts = prevMsg.artifacts;
          }
        }
        // For tool messages, use their own artifacts
        else if (msg.role === 'tool' && msg.artifacts && msg.artifacts.length > 0) {
          toolArtifacts = msg.artifacts;
        }
        
        return (
          <MessageBubble 
            key={msg.id} 
            message={msg} 
            toolArtifacts={toolArtifacts}
          />
        );
      })}
      {/* Inline typing bubble for assistant draft */}
      {streamingDraft && streamingDraft.threadId === currentThreadId && (
        <div className="flex gap-3 items-start">
          <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
            <Bot size={16} className="text-gray-600 dark:text-slate-400" />
          </div>
          <div className="flex-1 max-w-2xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg p-3">
            <p className="text-sm whitespace-pre-wrap">{streamingDraft.text}</p>
          </div>
        </div>
      )}

      {/* Inline tool execution drafts (no artifacts here) */}
      {toolDrafts
        .filter((t) => t.threadId === currentThreadId)
        .map((t, idx) => (
          <div key={`tool-draft-${idx}-${t.name}`} className="flex gap-3 items-start">
            <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
              <Wrench size={16} className="text-purple-600 dark:text-purple-400 animate-spin" />
            </div>
            <div className="flex-1 bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800 rounded-lg p-3">
              <div className="text-xs font-semibold text-purple-700 dark:text-purple-300 mb-1">
                {t.name}
              </div>
              {t.input && (
                <div className="text-xs text-gray-700 dark:text-slate-300">{formatParams(t.input)}</div>
              )}
            </div>
          </div>
        ))}
      
      {/* Artifact bubbles - shown during streaming for immediate feedback */}
      {artifactBubbles
        .filter((a) => a.threadId === currentThreadId)
        .map((a, idx) => (
          <div key={`artifact-${idx}-${a.toolName}`} className="space-y-3">
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="text-gray-600 dark:text-slate-400" />
              </div>
              <div className="flex-1 max-w-2xl">
                <ArtifactGrid artifacts={a.artifacts} />
              </div>
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
  toolArtifacts?: Message['artifacts'];
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

function MessageBubble({ message, toolArtifacts }: MessageBubbleProps) {
  const { role, content, artifacts } = message;
  
  // Combine message's own artifacts with tool artifacts from previous message
  const allArtifacts = [...(artifacts || []), ...(toolArtifacts || [])];

  // Tool messages: show with their artifacts
  if (role === 'tool') {
    return (
      <div className="space-y-3">
        <div className="flex gap-3 items-start">
          <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
            <Wrench size={16} className="text-purple-600 dark:text-purple-400" />
          </div>
          <div className="flex-1 bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800 rounded-lg p-3">
            <div className="text-xs font-semibold text-purple-700 dark:text-purple-300 mb-1">
              {message.tool_name || 'Tool'}
            </div>
            {message.tool_input && (
              <div className="text-xs text-gray-700 dark:text-slate-300 mb-2">
                {formatParams(message.tool_input)}
              </div>
            )}
            {message.tool_output && (
              <div className="text-xs text-gray-600 dark:text-slate-400">
                {formatParams(message.tool_output)}
              </div>
            )}
          </div>
        </div>
        {/* Show artifacts for tool messages */}
        {allArtifacts && allArtifacts.length > 0 && (
          <div className="flex gap-3 items-start">
            <div className="w-8 h-8 flex-shrink-0" /> {/* Spacer to align with message */}
            <div className="flex-1 max-w-2xl">
              <ArtifactGrid artifacts={allArtifacts} />
            </div>
          </div>
        )}
      </div>
    );
  }

  // User message rendering
  if (role === 'user') {
    return (
      <div className="flex gap-3 items-start justify-end">
        <div className="flex-1 max-w-2xl bg-blue-600 text-white rounded-lg p-3">
          <p className="text-sm whitespace-pre-wrap">
            {content?.text || JSON.stringify(content)}
          </p>
        </div>
        <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
          <User size={16} className="text-blue-600 dark:text-blue-400" />
        </div>
      </div>
    );
  }

  // Assistant message rendering
  if (role === 'assistant') {
    return (
      <div className="space-y-3">
        <div className="flex gap-3 items-start">
          <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
            <Bot size={16} className="text-gray-600 dark:text-slate-400" />
          </div>
          <div className="flex-1 max-w-2xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg p-3">
            <p className="text-sm whitespace-pre-wrap">
              {content?.text || JSON.stringify(content)}
            </p>
          </div>
        </div>
        {/* Show artifacts if this message has them or if tool message before it had artifacts */}
        {allArtifacts && allArtifacts.length > 0 && (
          <div className="flex gap-3 items-start">
            <div className="w-8 h-8 flex-shrink-0" /> {/* Spacer to align with message */}
            <div className="flex-1 max-w-2xl">
              <ArtifactGrid artifacts={allArtifacts} />
            </div>
          </div>
        )}
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

