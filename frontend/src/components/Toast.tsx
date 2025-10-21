/**
 * Toast: Modern toast notifications for errors and warnings.
 * Provides a clean, app-like notification system.
 */

import { useState, useEffect } from 'react';
import { X, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

export type ToastType = 'error' | 'success' | 'warning' | 'info';

interface ToastProps {
  type: ToastType;
  title: string;
  message?: string;
  duration?: number; // Auto-dismiss duration in ms (0 = no auto-dismiss)
  onClose?: () => void;
}

export function Toast({ type, title, message, duration = 5000, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [isExiting, setIsExiting] = useState(false);

  const icons = {
    error: AlertCircle,
    success: CheckCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const colors = {
    error: {
      bg: 'var(--error-500)',
      border: 'var(--error-600)',
      text: 'white',
      icon: 'white'
    },
    success: {
      bg: 'var(--success-500)',
      border: 'var(--success-600)',
      text: 'white',
      icon: 'white'
    },
    warning: {
      bg: 'var(--warning-500)',
      border: 'var(--warning-600)',
      text: 'white',
      icon: 'white'
    },
    info: {
      bg: 'var(--accent-600)',
      border: 'var(--accent-700)',
      text: 'white',
      icon: 'white'
    },
  };

  const Icon = icons[type];
  const colorScheme = colors[type];

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      setIsVisible(false);
      onClose?.();
    }, 200);
  };

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(handleClose, duration);
      return () => clearTimeout(timer);
    }
  }, [duration]);

  if (!isVisible) return null;

  return (
    <div
      className={`fixed top-4 right-4 z-50 max-w-sm w-full transition-all duration-200 ease-in-out transform ${
        isExiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'
      }`}
      style={{
        backgroundColor: colorScheme.bg,
        border: `1px solid ${colorScheme.border}`,
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-lg)'
      }}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <Icon size={20} style={{ color: colorScheme.icon, flexShrink: 0, marginTop: '2px' }} />
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-sm" style={{ color: colorScheme.text }}>
              {title}
            </h4>
            {message && (
              <p className="text-sm mt-1 opacity-90" style={{ color: colorScheme.text }}>
                {message}
              </p>
            )}
          </div>
          <button
            onClick={handleClose}
            className="flex-shrink-0 p-1 rounded-full hover:bg-black/10 transition-colors"
            style={{ color: colorScheme.text }}
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

// Toast Manager for global toast notifications
interface ToastManagerProps {
  toasts: Array<ToastProps & { id: string }>;
  onRemove: (id: string) => void;
}

export function ToastManager({ toasts, onRemove }: ToastManagerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          {...toast}
          onClose={() => onRemove(toast.id)}
        />
      ))}
    </div>
  );
}
