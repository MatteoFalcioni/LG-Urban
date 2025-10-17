/**
 * Global state management using Zustand.
 * Handles threads, messages, and UI state.
 */

import { create } from 'zustand';
import type { Thread, Message, Artifact } from '@/types/api';

interface ChatStore {
  // User identity (anonymous UUID stored in localStorage)
  userId: string;
  setUserId: (id: string) => void;

  // Threads
  threads: Thread[];
  setThreads: (threads: Thread[]) => void;
  addThread: (thread: Thread) => void;
  updateThread: (threadId: string, updates: Partial<Thread>) => void;

  // Current selected thread
  currentThreadId: string | null;
  setCurrentThreadId: (id: string | null) => void;

  // Messages for current thread
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;

  // Streaming draft for inline assistant typing bubble
  streamingDraft: { threadId: string; text: string } | null;
  setStreamingDraft: (threadId: string, text: string) => void;
  clearStreamingDraft: () => void;

  // Live tool execution drafts shown inline while tools run
  toolDrafts: { threadId: string; name: string; input?: any }[];
  addToolDraft: (threadId: string, name: string, input?: any) => void;
  removeToolDraft: (threadId: string, name: string) => void;
  clearToolDrafts: (threadId: string) => void;
  
  // Artifact bubbles (separate from tool drafts, persistent)
  artifactBubbles: { threadId: string; toolName: string; artifacts: Artifact[] }[];
  addArtifactBubble: (threadId: string, toolName: string, artifacts: Artifact[]) => void;
  clearArtifactBubbles: (threadId: string) => void;

  // UI state
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  isConfigPanelOpen: boolean;
  toggleConfigPanel: () => void;
  theme: 'light' | 'dark' | 'auto';
  setTheme: (theme: 'light' | 'dark' | 'auto') => void;

  // Sidebar width (resizable with limits)
  sidebarWidth: number;
  setSidebarWidth: (px: number) => void;

  // Default configs for new threads (applied when auto-creating)
  defaultConfig: { model: string | null; temperature: number | null; system_prompt: string | null; context_window: number | null };
  setDefaultConfig: (config: { model?: string | null; temperature?: number | null; system_prompt?: string | null; context_window?: number | null }) => void;

  // Context usage tracking
  contextUsage: { tokensUsed: number; maxTokens: number };
  setContextUsage: (tokensUsed: number, maxTokens: number) => void;
  isSummarizing: boolean;
  setIsSummarizing: (value: boolean) => void;

  // Bulk selection for threads
  selectedThreadIds: Set<string>;
  toggleThreadSelection: (threadId: string) => void;
  selectAllThreads: (threadIds: string[]) => void;
  clearThreadSelection: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  // Initialize user ID from localStorage or generate new
  userId: (() => {
    const stored = localStorage.getItem('userId');
    if (stored) return stored;
    const newId = crypto.randomUUID();
    localStorage.setItem('userId', newId);
    return newId;
  })(),
  setUserId: (id) => {
    localStorage.setItem('userId', id);
    set({ userId: id });
  },

  threads: [],
  setThreads: (threads) => set({ threads }),
  addThread: (thread) => set((state) => ({ threads: [thread, ...state.threads] })),
  updateThread: (threadId, updates) =>
    set((state) => ({
      threads: state.threads.map((t) => (t.id === threadId ? { ...t, ...updates } : t)),
    })),

  currentThreadId: null,
  setCurrentThreadId: (id) => set({ currentThreadId: id, messages: [] }),

  messages: [],
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateMessage: (messageId, updates) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === messageId ? { ...m, ...updates } : m)),
    })),

  streamingDraft: null,
  setStreamingDraft: (threadId, text) => set({ streamingDraft: { threadId, text } }),
  clearStreamingDraft: () => set({ streamingDraft: null }),

  toolDrafts: [],
  addToolDraft: (threadId, name, input) =>
    set((state) => ({ toolDrafts: [...state.toolDrafts, { threadId, name, input }] })),
  removeToolDraft: (threadId, name) =>
    set((state) => ({ toolDrafts: state.toolDrafts.filter((t) => !(t.threadId === threadId && t.name === name)) })),
  clearToolDrafts: (threadId) =>
    set((state) => ({ toolDrafts: state.toolDrafts.filter((t) => t.threadId !== threadId) })),
  
  artifactBubbles: [],
  addArtifactBubble: (threadId, toolName, artifacts) =>
    set((state) => ({ artifactBubbles: [...state.artifactBubbles, { threadId, toolName, artifacts }] })),
  clearArtifactBubbles: (threadId) =>
    set((state) => ({ artifactBubbles: state.artifactBubbles.filter((a) => a.threadId !== threadId) })),

  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  
  isConfigPanelOpen: false,
  toggleConfigPanel: () => set((state) => ({ isConfigPanelOpen: !state.isConfigPanelOpen })),

  theme: (localStorage.getItem('theme') as any) || 'auto',
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    set({ theme });
  },

  sidebarWidth: parseInt(localStorage.getItem('sidebarWidth') || '256', 10),
  setSidebarWidth: (px) => {
    const clamped = Math.max(220, Math.min(420, px));
    localStorage.setItem('sidebarWidth', String(clamped));
    set({ sidebarWidth: clamped });
  },

  defaultConfig: JSON.parse(localStorage.getItem('defaultConfig') || '{"model":null,"temperature":null,"system_prompt":null,"context_window":null}'),
  setDefaultConfig: (updates) => {
    set((state) => {
      const newConfig = { ...state.defaultConfig, ...updates };
      localStorage.setItem('defaultConfig', JSON.stringify(newConfig));
      return { defaultConfig: newConfig };
    });
  },

  contextUsage: { tokensUsed: 0, maxTokens: 30000 },
  setContextUsage: (tokensUsed, maxTokens) => set({ contextUsage: { tokensUsed, maxTokens } }),
  isSummarizing: false,
  setIsSummarizing: (value) => set({ isSummarizing: value }),

  selectedThreadIds: new Set(),
  toggleThreadSelection: (threadId) =>
    set((state) => {
      const newSelected = new Set(state.selectedThreadIds);
      if (newSelected.has(threadId)) {
        newSelected.delete(threadId);
      } else {
        newSelected.add(threadId);
      }
      return { selectedThreadIds: newSelected };
    }),
  selectAllThreads: (threadIds) => set({ selectedThreadIds: new Set(threadIds) }),
  clearThreadSelection: () => set({ selectedThreadIds: new Set() }),
}));

