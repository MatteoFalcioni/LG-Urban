/**
 * Main App component with routing.
 * Routes: / (ChatPage), /settings (SettingsPage)
 */

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import { useChatStore } from '@/store/chatStore';
import { ToastManager } from '@/components/Toast';
import { useClerkSync } from '@/hooks/useClerkSync';
import { useApiKeysLoader } from '@/hooks/useApiKeysLoader';
import { ChatPage } from '@/pages/ChatPage';
import { SettingsPage } from '@/pages/SettingsPage';

function App() {
  // Sync Clerk authentication with chat store
  useClerkSync();
  // Load API keys when userId is available
  useApiKeysLoader();
  const theme = useChatStore((state) => state.theme);
  const toasts = useChatStore((state) => state.toasts);
  const removeToast = useChatStore((state) => state.removeToast);

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

  return (
    <>
      <SignedIn>
        {/* User is signed in - show app */}
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>

          {/* Toast notifications (global) */}
          <ToastManager toasts={toasts} onRemove={removeToast} />
        </BrowserRouter>
      </SignedIn>

      <SignedOut>
        {/* User is signed out - redirect to sign in */}
        <RedirectToSignIn />
      </SignedOut>
    </>
  );
}

export default App;
