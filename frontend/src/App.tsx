/**
 * Main App component.
 * Layout: [Sidebar] [MessageView] [ConfigPanel?]
 */

import { useEffect, useRef, useState } from 'react';
import { Settings } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { ThreadSidebar } from '@/components/ThreadSidebar';
import { MessageList } from '@/components/MessageList';
import { MessageInput } from '@/components/MessageInput';
import { ConfigPanel } from '@/components/ConfigPanel';
import { ContextIndicator } from '@/components/ContextIndicator';

function App() {
  const theme = useChatStore((state) => state.theme);
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const toggleConfigPanel = useChatStore((state) => state.toggleConfigPanel);
  const sidebarWidth = useChatStore((s) => s.sidebarWidth);
  const setSidebarWidth = useChatStore((s) => s.setSidebarWidth);
  const contextUsage = useChatStore((s) => s.contextUsage);
  const isSummarizing = useChatStore((s) => s.isSummarizing);
  const defaultConfig = useChatStore((s) => s.defaultConfig);
  
  // Use context_window from defaultConfig if contextUsage.maxTokens is still default
  const effectiveMaxTokens = contextUsage.maxTokens === 30000 && defaultConfig.context_window 
    ? defaultConfig.context_window 
    : contextUsage.maxTokens;
  const isResizing = useRef(false);
  const startWidth = useRef(0);
  const startX = useRef(0);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Apply theme to document root
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else if (theme === 'light') {
      root.classList.remove('dark');
    } else {
      // Auto: match system preference
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (isDark) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
  }, [theme]);

  // Handle resize start and attach listeners directly
  function handleResizeStart(e: React.MouseEvent) {
    e.preventDefault();
    isResizing.current = true;
    startX.current = e.clientX;
    startWidth.current = sidebarWidth;

    function handleMouseMove(e: MouseEvent) {
      if (!isResizing.current) return;
      const delta = e.clientX - startX.current;
      const newWidth = startWidth.current + delta;
      setSidebarWidth(newWidth);
    }

    function handleMouseUp() {
      isResizing.current = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    }

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-slate-900 text-gray-900 dark:text-slate-100">
      {/* Sidebar: Thread list (resizable/collapsible) */}
      {!isSidebarCollapsed && (
        <aside
          className="bg-white dark:bg-slate-800 border-r border-gray-200 dark:border-slate-700 relative"
          style={{ width: sidebarWidth }}
        >
          <ThreadSidebar />
          {/* Resize handle */}
          <div
            onMouseDown={handleResizeStart}
            className="absolute top-0 right-0 w-2 h-full cursor-col-resize hover:bg-blue-500/20 bg-transparent"
          />
        </aside>
      )}

      {/* Collapse/expand button */}
      <button
        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        className="fixed top-4 left-4 z-10 p-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-slate-700"
      >
        {isSidebarCollapsed ? '→' : '←'}
      </button>

      {/* Main content: Messages */}
      <main className="flex-1 flex flex-col">
        {/* Header with context indicator and config toggle */}
        <div className="flex items-center justify-between p-2 border-b border-gray-200 dark:border-slate-700">
          <ContextIndicator 
            tokensUsed={contextUsage.tokensUsed}
            maxTokens={effectiveMaxTokens}
            isSummarizing={isSummarizing}
          />
          <button
            onClick={toggleConfigPanel}
            className="p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title={currentThreadId ? 'Thread Settings' : 'Default Settings'}
          >
            <Settings size={18} className="text-gray-600 dark:text-slate-400" />
          </button>
        </div>
        
        <div className="flex-1 overflow-auto p-6">
          <MessageList />
        </div>
        
        {/* Message input with streaming support */}
        <MessageInput />
      </main>

      {/* Right panel: Config (toggleable) */}
      <ConfigPanel />
    </div>
  );
}

export default App;

