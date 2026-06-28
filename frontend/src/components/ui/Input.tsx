'use client';

import { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error = false, className = '', ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={[
          'w-full px-3 py-2 rounded border font-sans text-base',
          'bg-surface text-primary',
          'transition-colors duration-fast',
          'placeholder:text-tertiary',
          'focus:outline-none focus:border-[var(--color-border-focus)]',
          'focus:shadow-[0_0_0_3px_rgba(230,172,0,0.18)]',
          'hover:border-[color:var(--color-border-strong)]',
          'disabled:bg-sunken disabled:text-disabled disabled:cursor-not-allowed',
          error
            ? 'border-[color:var(--color-danger-border)]'
            : 'border-[color:var(--color-border-default)]',
          className,
        ]
          .filter(Boolean)
          .join(' ')}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

interface InputAmountProps extends Omit<InputProps, 'type'> {
  currency?: string;
}

export const InputAmount = forwardRef<HTMLInputElement, InputAmountProps>(
  ({ currency = 'ETB', className = '', ...props }, ref) => {
    return (
      <div className="relative">
        <span
          aria-hidden="true"
          className="absolute left-3 top-1/2 -translate-y-1/2 text-tertiary font-mono text-sm pointer-events-none select-none"
        >
          {currency}
        </span>
        <Input
          ref={ref}
          type="number"
          inputMode="decimal"
          className={[
            'font-mono font-semibold text-md text-right pr-3',
            currency ? 'pl-11' : '',
            className,
          ]
            .filter(Boolean)
            .join(' ')}
          {...props}
        />
      </div>
    );
  }
);
InputAmount.displayName = 'InputAmount';
