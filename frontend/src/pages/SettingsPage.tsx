/**
 * SettingsPage: Full page for thread-specific or default configuration.
 * - When thread is selected: shows and saves thread-specific config
 * - When no thread: shows and saves default config for new threads
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Settings, Eye, EyeOff, Key } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { getDefaultConfig, getThreadConfig, updateThreadConfig, getUserApiKeys, saveUserApiKeys } from '@/utils/api';
import type { ThreadConfig } from '@/types/api';

export function SettingsPage() {
  const navigate = useNavigate();
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const userId = useChatStore((state) => state.userId);
  const defaultConfig = useChatStore((state) => state.defaultConfig);
  const setDefaultConfig = useChatStore((state) => state.setDefaultConfig);
  const setApiKeys = useChatStore((state) => state.setApiKeys);

  const [config, setConfig] = useState<ThreadConfig>({
    model: null,
    temperature: null,
    system_prompt: null,
    context_window: null,
    settings: null,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // API Keys state
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isSavingKeys, setIsSavingKeys] = useState(false);
  const [keysSaveStatus, setKeysSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Load config when thread changes
  useEffect(() => {
    async function loadConfig() {
      if (!currentThreadId) {
        // No thread: use local store defaults if available, otherwise fetch from backend
        if (defaultConfig.model || defaultConfig.temperature !== null || defaultConfig.system_prompt || defaultConfig.context_window !== null) {
          // Use local store defaults (user has saved custom defaults)
          console.log('Using local store defaults:', defaultConfig);
          setConfig({
            model: defaultConfig.model,
            temperature: defaultConfig.temperature,
            system_prompt: defaultConfig.system_prompt,
            context_window: defaultConfig.context_window,
            settings: null,
          });
        } else {
          // No local defaults: fetch backend defaults
          try {
            const cfg = await getDefaultConfig();
            console.log('Fetched backend defaults:', cfg);
            setConfig(cfg);
            // Also update store's defaultConfig with backend values
            setDefaultConfig({
              model: cfg.model,
              temperature: cfg.temperature,
              system_prompt: cfg.system_prompt,
              context_window: cfg.context_window,
            });
          } catch (err) {
            console.error('Failed to load default config:', err);
            // Fallback to localStorage defaults if API fails
            setConfig({
              model: defaultConfig.model,
              temperature: defaultConfig.temperature,
              system_prompt: defaultConfig.system_prompt,
              context_window: defaultConfig.context_window,
              settings: null,
            });
          }
        }
        return;
      }

      // Thread selected: load thread-specific config
      try {
        const cfg = await getThreadConfig(currentThreadId!);
        console.log('Loaded thread config:', cfg);
        console.log('Config model value:', cfg.model);
        setConfig(cfg);
      } catch (err) {
        console.error('Failed to load config:', err);
      }
    }
    loadConfig();
  }, [currentThreadId, defaultConfig, setDefaultConfig]);

  // Load API keys on mount
  useEffect(() => {
    async function loadApiKeys() {
      try {
        const keys = await getUserApiKeys(userId);
        // Don't set masked keys in inputs - they're just for display/checking existence
        // Leave input empty so user can enter new key
        setApiKeyInput('');
        // Update store to track if key exists (for warning modal)
        setApiKeys({
          openrouter: keys.openrouter_key || null,
        });
      } catch (err) {
        console.error('Failed to load API keys:', err);
      }
    }
    loadApiKeys();
  }, [userId, setApiKeys]);

  /**
   * Save config: thread-specific or default depending on selection
   */
  async function handleSave() {
    setIsSaving(true);
    setSaveStatus('idle');
    try {
      console.log('Saving config:', config);
      console.log('Current thread ID:', currentThreadId);
      if (!currentThreadId) {
        // No thread selected: update local store only (session-local defaults)
        // Note: These won't persist across browser sessions
        setDefaultConfig({
          model: config.model,
          temperature: config.temperature,
          system_prompt: config.system_prompt,
          context_window: config.context_window,
        });
        setSaveStatus('success');
        setTimeout(() => setSaveStatus('idle'), 2000);
      } else {
        // Save thread-specific config (POST /threads/:id/config)
        console.log('Calling updateThreadConfig with:', { threadId: currentThreadId, config });
        const result = await updateThreadConfig(currentThreadId, config);
        console.log('Config saved successfully:', result);
        setSaveStatus('success');
        setTimeout(() => setSaveStatus('idle'), 2000);
      }
    } catch (err) {
      console.error('Failed to save config:', err);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  }

  /**
   * Save API key
   */
  async function handleSaveApiKeys() {
    setIsSavingKeys(true);
    setKeysSaveStatus('idle');
    try {
      // Only send key if entered (non-empty)
      const keysToSave: { openrouter_key?: string | null } = {};
      if (apiKeyInput) {
        keysToSave.openrouter_key = apiKeyInput;
      }

      await saveUserApiKeys(userId, keysToSave);

      // Update store with the key that was saved
      if (apiKeyInput) {
        setApiKeys({ openrouter: apiKeyInput });
      }

      setKeysSaveStatus('success');

      // Redirect to chat after successful save (so warning disappears)
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (err) {
      console.error('Failed to save API key:', err);
      setKeysSaveStatus('error');
    } finally {
      setIsSavingKeys(false);
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-slate-900 text-gray-700 dark:text-slate-200 overflow-hidden">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex-shrink-0">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title="Back to chat"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-3 flex-1">
            <Settings size={24} className="text-gray-600 dark:text-slate-400" />
            <div>
              <h1 className="text-xl font-semibold">Settings</h1>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                {currentThreadId ? 'Thread-specific configuration' : 'Default configuration for new threads'}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main content - scrollable area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Model Configuration */}
        <section className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Settings size={18} className="text-gray-600 dark:text-slate-400" />
            Model Configuration
          </h2>

          <div className="space-y-4">
            {/* Model Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Model</label>
              <select
                value={config.model || defaultConfig.model || 'claude-sonnet-4.6'}
                onChange={(e) => {
                  console.log('Model changed to:', e.target.value);
                  setConfig((prev) => ({ ...prev, model: e.target.value }));
                }}
                onFocus={() => {
                  console.log('Select focused - current config.model:', config.model);
                  console.log('Select focused - defaultConfig.model:', defaultConfig.model);
                  console.log('Select focused - computed value:', config.model || defaultConfig.model || 'claude-sonnet-4.6');
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-gray-800 dark:focus:ring-gray-600 focus:border-gray-800 dark:focus:border-gray-600 transition-all outline-none"
                style={{
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)'
                }}
              >
                <option value="gpt-5.5">GPT-5.5</option>
                <option value="kimi-k2.6">Kimi k2.6</option>
                <option value="minimax-m2.7">MiniMax M2.7</option>
                <option value="claude-sonnet-4.6">Claude Sonnet 4.6</option>
                <option value="claude-opus-4.6">Claude Opus 4.6</option>
              </select>
            </div>

            {/* Temperature */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Temperature: {config.temperature ?? defaultConfig.temperature ?? 0.5}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={config.temperature ?? defaultConfig.temperature ?? 0.5}
                onChange={(e) => setConfig((prev) => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                className="w-full h-2 rounded-lg cursor-pointer range-slider"
                style={{
                  background: `linear-gradient(to right, #1f2937 0%, #1f2937 ${((config.temperature ?? defaultConfig.temperature ?? 0.5) / 1) * 100}%, #e5e7eb ${((config.temperature ?? defaultConfig.temperature ?? 0.5) / 1) * 100}%, #e5e7eb 100%)`
                }}
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400 mt-1">
                <span>Precise (0.0)</span>
                <span>Creative (1.0)</span>
              </div>
            </div>

            {/* Context Window */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Context Window: {(config.context_window ?? defaultConfig.context_window ?? 200000).toLocaleString()} tokens
              </label>
              <input
                type="number"
                min="1000"
                max="200000"
                step="1000"
                value={config.context_window ?? defaultConfig.context_window ?? 200000}
                onChange={(e) => setConfig((prev) => ({ ...prev, context_window: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-gray-800 dark:focus:ring-gray-600 focus:border-gray-800 dark:focus:border-gray-600 transition-all outline-none"
                style={{
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)'
                }}
              />
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                Maximum context size before summarization (default: 200k context window)
              </p>
              {(config.context_window ?? defaultConfig.context_window ?? 200000) > 200000 && (
                <div className="mt-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-xs text-yellow-800 dark:text-yellow-200">
                    ⚠️ <strong>Note:</strong> Context windows larger than 200k may not be supported by all models. Check OpenRouter model documentation for supported context sizes.
                  </p>
                </div>
              )}
            </div>

            {/* System Prompt */}
            <div>
              <label className="block text-sm font-medium mb-2">System Prompt</label>
              <textarea
                value={config.system_prompt ?? defaultConfig.system_prompt ?? ''}
                onChange={(e) => setConfig((prev) => ({ ...prev, system_prompt: e.target.value }))}
                rows={6}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-gray-800 dark:focus:ring-gray-600 focus:border-gray-800 dark:focus:border-gray-600 transition-all resize-none outline-none"
                style={{
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)'
                }}
              />
            </div>

            {/* Save Button */}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="w-full px-4 py-2 bg-gray-800 hover:bg-gray-900 dark:bg-gray-700 dark:hover:bg-gray-600 text-white rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Save size={16} />
              {isSaving ? 'Saving...' : 'Save Configuration'}
            </button>

            {saveStatus === 'success' && (
              <p className="text-sm text-green-600 dark:text-green-400 text-center">
                ✓ Configuration saved successfully
              </p>
            )}
            {saveStatus === 'error' && (
              <p className="text-sm text-red-600 dark:text-red-400 text-center">
                ✗ Failed to save configuration
              </p>
            )}
          </div>
        </section>

        {/* API Key Section */}
        <section className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Key size={18} className="text-gray-600 dark:text-slate-400" />
            OpenRouter API Key
          </h2>

          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-slate-400">
              Your OpenRouter API key is encrypted and stored securely. Get your key from{' '}
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:text-blue-600 underline"
              >
                openrouter.ai/keys
              </a>
            </p>

            {/* OpenRouter Key */}
            <div>
              <label className="block text-sm font-medium mb-2">API Key</label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder="sk-or-v1-... (enter new key or leave empty to keep existing)"
                  className="w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-gray-800 dark:focus:ring-gray-600 focus:border-gray-800 dark:focus:border-gray-600 transition-all outline-none"
                  style={{
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)'
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded"
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Save Key Button */}
            <button
              onClick={handleSaveApiKeys}
              disabled={isSavingKeys}
              className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Save size={16} />
              {isSavingKeys ? 'Saving...' : 'Save API Key'}
            </button>

            {keysSaveStatus === 'success' && (
              <p className="text-sm text-green-600 dark:text-green-400 text-center">
                ✓ API key saved successfully
              </p>
            )}
            {keysSaveStatus === 'error' && (
              <p className="text-sm text-red-600 dark:text-red-400 text-center">
                ✗ Failed to save API key
              </p>
            )}
          </div>
        </section>
        </div>
      </main>
    </div>
  );
}
