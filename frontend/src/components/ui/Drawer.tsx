'use client';

import { Dialog, DialogPanel, DialogTitle, DialogBackdrop } from '@headlessui/react';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

export function Drawer({ open, onClose, title, footer, children }: DrawerProps) {
  return (
    <Dialog open={open} onClose={onClose} className="relative z-[400]">
      <DialogBackdrop
        className="fixed inset-0 bg-[var(--color-bg-overlay)]"
        transition
      />
      <div className="fixed inset-0 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full">
            <DialogPanel className="pointer-events-auto w-screen max-w-[min(560px,100vw)]">
              <div className="flex h-full flex-col bg-surface border-l border-[color:var(--color-border-default)] shadow-xl overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-[color:var(--color-border-default)] flex-shrink-0">
                  <DialogTitle className="text-xl font-semibold text-primary">
                    {title}
                  </DialogTitle>
                  <button
                    onClick={onClose}
                    aria-label="Close drawer"
                    className="text-tertiary hover:text-primary transition-colors duration-fast rounded focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-2"
                  >
                    <CloseIcon />
                  </button>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto p-6">{children}</div>

                {/* Footer */}
                {footer && (
                  <div className="flex-shrink-0 flex items-center justify-end gap-3 px-6 py-4 border-t border-[color:var(--color-border-default)]">
                    {footer}
                  </div>
                )}
              </div>
            </DialogPanel>
          </div>
        </div>
      </div>
    </Dialog>
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
