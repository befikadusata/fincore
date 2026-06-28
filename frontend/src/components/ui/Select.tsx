'use client';

import { forwardRef } from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ error = false, className = '', children, ...props }, ref) => {
    return (
      <div className="relative">
        <select
          ref={ref}
          className={[
            'w-full px-3 py-2 pr-8 rounded border font-sans text-base',
            'bg-surface text-primary',
            'transition-colors duration-fast',
            'focus:outline-none focus:border-[var(--color-border-focus)]',
            'focus:shadow-[0_0_0_3px_rgba(230,172,0,0.18)]',
            'hover:border-[color:var(--color-border-strong)]',
            'disabled:bg-sunken disabled:text-disabled disabled:cursor-not-allowed',
            'appearance-none cursor-pointer',
            error
              ? 'border-[color:var(--color-danger-border)]'
              : 'border-[color:var(--color-border-default)]',
            className,
          ]
            .filter(Boolean)
            .join(' ')}
          {...props}
        >
          {children}
        </select>
        <svg
          className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-tertiary pointer-events-none"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    );
  }
);
Select.displayName = 'Select';
