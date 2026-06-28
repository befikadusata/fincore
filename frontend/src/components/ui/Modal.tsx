'use client';

import { Dialog, DialogPanel, DialogTitle, DialogBackdrop } from '@headlessui/react';
import { Button } from './Button';

type ModalSize = 'sm' | 'md' | 'lg';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  size?: ModalSize;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

const sizeClasses: Record<ModalSize, string> = {
  sm: 'max-w-[400px]',
  md: 'max-w-[560px]',
  lg: 'max-w-[720px]',
};

export function Modal({
  open,
  onClose,
  title,
  size = 'md',
  footer,
  children,
}: ModalProps) {
  return (
    <Dialog open={open} onClose={onClose} className="relative z-[400]">
      <DialogBackdrop
        className="fixed inset-0 bg-[var(--color-bg-overlay)]"
        transition
      />
      <div className="fixed inset-0 flex items-center justify-center p-4 overflow-y-auto">
        <DialogPanel
          className={[
            'w-full bg-surface border border-[color:var(--color-border-default)]',
            'rounded-xl shadow-xl max-h-[calc(100vh-4rem)] overflow-y-auto',
            sizeClasses[size],
          ].join(' ')}
        >
          {/* Sticky header */}
          <div className="sticky top-0 bg-surface flex items-center justify-between px-6 py-5 border-b border-[color:var(--color-border-default)]">
            <DialogTitle className="text-xl font-semibold text-primary">
              {title}
            </DialogTitle>
            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="text-tertiary hover:text-primary transition-colors duration-fast rounded focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-2"
            >
              <CloseIcon />
            </button>
          </div>

          {/* Body */}
          <div className="p-6">{children}</div>

          {/* Sticky footer */}
          {footer && (
            <div className="sticky bottom-0 bg-surface flex items-center justify-end gap-3 px-6 py-4 border-t border-[color:var(--color-border-default)]">
              {footer}
            </div>
          )}
        </DialogPanel>
      </div>
    </Dialog>
  );
}

/** Convenience footer with Cancel + primary action button. */
export function ModalFooter({
  onCancel,
  onConfirm,
  confirmLabel = 'Confirm',
  confirmVariant = 'primary',
  loading = false,
}: {
  onCancel: () => void;
  onConfirm: () => void;
  confirmLabel?: string;
  confirmVariant?: 'primary' | 'danger';
  loading?: boolean;
}) {
  return (
    <>
      <Button variant="secondary" onClick={onCancel} disabled={loading}>
        Cancel
      </Button>
      <Button variant={confirmVariant} onClick={onConfirm} loading={loading}>
        {confirmLabel}
      </Button>
    </>
  );
}

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}
