'use client';

import {
  createContext,
  useCallback,
  useContext,
  useId,
  useState,
} from 'react';

type ToastVariant = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  variant: ToastVariant;
  title: string;
  message?: string;
}

interface ToastContextValue {
  toast: {
    success: (title: string, message?: string) => void;
    error:   (title: string, message?: string) => void;
    warning: (title: string, message?: string) => void;
    info:    (title: string, message?: string) => void;
  };
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const baseId = useId();
  let counter = 0;

  const addToast = useCallback(
    (variant: ToastVariant, title: string, message?: string) => {
      const id = `${baseId}-${Date.now()}-${counter++}`;
      setToasts((prev) => [...prev, { id, variant, title, message }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    },
    [baseId]
  );

  const toast = {
    success: (title: string, message?: string) => addToast('success', title, message),
    error:   (title: string, message?: string) => addToast('error',   title, message),
    warning: (title: string, message?: string) => addToast('warning', title, message),
    info:    (title: string, message?: string) => addToast('info',    title, message),
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <ToastRegion toasts={toasts} onDismiss={(id) => setToasts((p) => p.filter((t) => t.id !== id))} />
    </ToastContext.Provider>
  );
}

const variantClasses: Record<ToastVariant, string> = {
  success: 'border-[color:var(--color-success-border)] border-l-[3px] border-l-[color:var(--color-success-rail)]',
  error:   'border-[color:var(--color-danger-border)]  border-l-[3px] border-l-[color:var(--color-danger-rail)]',
  warning: 'border-[color:var(--color-warning-border)] border-l-[3px] border-l-[color:var(--color-warning-rail)]',
  info:    'border-[color:var(--color-info-border)]    border-l-[3px] border-l-[color:var(--color-info-rail)]',
};

const variantIcons: Record<ToastVariant, string> = {
  success: '✓',
  error:   '✕',
  warning: '⚠',
  info:    'ℹ',
};

const iconColorClasses: Record<ToastVariant, string> = {
  success: 'text-[var(--color-success-text)]',
  error:   'text-[var(--color-danger-text)]',
  warning: 'text-[var(--color-warning-text)]',
  info:    'text-[var(--color-info-text)]',
};

function ToastRegion({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Notifications"
      className="fixed bottom-6 right-6 z-[500] flex flex-col gap-3 max-w-[380px] w-full"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          className={[
            'flex items-start gap-3 p-4 rounded-lg border shadow-lg bg-surface text-sm',
            variantClasses[t.variant],
          ].join(' ')}
        >
          <span
            aria-hidden="true"
            className={`font-bold text-base leading-none mt-0.5 flex-shrink-0 ${iconColorClasses[t.variant]}`}
          >
            {variantIcons[t.variant]}
          </span>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-primary">{t.title}</p>
            {t.message && (
              <p className="text-secondary mt-0.5">{t.message}</p>
            )}
          </div>
          <button
            onClick={() => onDismiss(t.id)}
            aria-label="Dismiss notification"
            className="text-tertiary hover:text-primary transition-colors duration-fast flex-shrink-0"
          >
            <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
