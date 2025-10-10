/**
 * ConfigPanel: right-side panel for thread-specific or default configuration.
 * - When thread is selected: shows and saves thread-specific config
 * - When no thread: shows and saves default config for new threads
 */

import { useEffect, useState } from 'react';
import { X, Save, Settings } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { getDefaultConfig, getThreadConfig, updateThreadConfig } from '@/utils/api';
import type { ThreadConfig } from '@/types/api';

export function ConfigPanel() {
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const isOpen = useChatStore((state) => state.isConfigPanelOpen);
  const toggleConfigPanel = useChatStore((state) => state.toggleConfigPanel);
  const defaultConfig = useChatStore((state) => state.defaultConfig);
  const setDefaultConfig = useChatStore((state) => state.setDefaultConfig);
  const contextUsage = useChatStore((state) => state.contextUsage);
  const setContextUsage = useChatStore((state) => state.setContextUsage);

  const [config, setConfig] = useState<ThreadConfig>({
    model: null,
    temperature: null,
    system_prompt: null,
    context_window: null,
    settings: null,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Load config when thread changes
  useEffect(() => {
    async function loadConfig() {
      if (!currentThreadId) {
        // No thread: fetch backend defaults from /config/defaults
        try {
          const cfg = await getDefaultConfig();
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
        return;
      }

      // Thread selected: load thread-specific config
      try {
        const cfg = await getThreadConfig(currentThreadId!);
        setConfig(cfg);
      } catch (err) {
        console.error('Failed to load config:', err);
      }
    }
    loadConfig();
  }, [currentThreadId]);

  /**
   * Save config: thread-specific or default depending on selection
   */
  async function handleSave() {
    setIsSaving(true);
    setSaveStatus('idle');

    try {
      if (currentThreadId) {
        // Save thread-specific config
        const updated = await updateThreadConfig(currentThreadId, config);
        setConfig(updated);
        // Update context circle immediately with new context_window
        if (updated.context_window !== null && updated.context_window !== undefined) {
          setContextUsage(contextUsage.tokensUsed, updated.context_window);
        }
      } else {
        // Save as default config for new threads
        setDefaultConfig({
          model: config.model,
          temperature: config.temperature,
          system_prompt: config.system_prompt,
          context_window: config.context_window,
        });
        // Update context circle with new default context_window
        if (config.context_window !== null && config.context_window !== undefined) {
          setContextUsage(contextUsage.tokensUsed, config.context_window);
        }
      }
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err) {
      console.error('Failed to save config:', err);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  }

  if (!isOpen) return null;

  return (
    <aside className="w-80 bg-white dark:bg-slate-800 border-l border-gray-200 dark:border-slate-700 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <Settings size={18} className="text-gray-600 dark:text-slate-400" />
          <h2 className="font-semibold">
            {currentThreadId ? 'Thread Config' : 'Default Settings'}
          </h2>
        </div>
        <button
          onClick={toggleConfigPanel}
          className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded"
        >
          <X size={18} />
        </button>
      </div>

      {/* Config form */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {!currentThreadId && (
          <p className="text-xs text-gray-600 dark:text-slate-400 mb-4">
            These settings will be applied to new chats you create.
          </p>
        )}

        {/* Model selection */}
        <div>
          <label className="block text-sm font-medium mb-1">Model</label>
          <select
            value={config.model || 'gpt-4o'}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4o-mini">GPT-4o Mini</option>
            <option value="gpt-4.1">GPT-4.1</option>
            <option value="gpt-5">GPT-5</option>
          </select>
        </div>

        {/* Temperature slider */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Temperature: {config.temperature?.toFixed(1) || '0.7'}
          </label>
          <input
            type="range"
            min="0.0"
            max="2.0"
            step="0.1"
            value={config.temperature ?? 0.7}
            onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
            className="w-full accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400 mt-1">
            <span>Precise (0.0)</span>
            <span>Creative (2.0)</span>
          </div>
        </div>

        {/* Context Window */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Context Window: {(config.context_window ?? defaultConfig.context_window ?? 30000).toLocaleString()} tokens
          </label>
          <input
            type="number"
            min="1000"
            max="200000"
            step="1000"
            value={config.context_window ?? defaultConfig.context_window ?? 30000}
            onChange={(e) => setConfig({ ...config, context_window: parseInt(e.target.value) || null })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          />
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
            Maximum context size before summarization (GPT-4o: 128k, Base tier: 30k)
          </p>
        </div>

        {/* Custom Instructions (added to default prompt) */}
        <div>
          <label className="block text-sm font-medium mb-1">Custom Instructions</label>
          <textarea
            value={config.system_prompt || ''}
            onChange={(e) => setConfig({ ...config, system_prompt: e.target.value })}
            placeholder="Custom instructions for the assistant"
            rows={6}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-sm"
          />
        </div>
      </div>

      {/* Footer with save button */}
      <div className="p-4 border-t border-gray-200 dark:border-slate-700">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-slate-700 text-white rounded-lg transition-colors"
        >
          <Save size={18} />
          <span>{isSaving ? 'Saving...' : 'Save Config'}</span>
        </button>
        
        {/* Save status feedback */}
        {saveStatus === 'success' && (
          <p className="text-xs text-green-600 dark:text-green-400 mt-2 text-center">✓ Saved successfully</p>
        )}
        {saveStatus === 'error' && (
          <p className="text-xs text-red-600 dark:text-red-400 mt-2 text-center">✗ Failed to save</p>
        )}
      </div>
    </aside>
  );
}
