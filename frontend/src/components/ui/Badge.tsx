import type { BadgeVariant } from '@/lib/status';

interface BadgeProps {
  variant?: BadgeVariant;
  dot?: boolean;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'bg-[var(--color-success-bg)] text-[var(--color-success-text)]',
  info:    'bg-[var(--color-info-bg)] text-[var(--color-info-text)]',
  warning: 'bg-[var(--color-warning-bg)] text-[var(--color-warning-text)]',
  danger:  'bg-[var(--color-danger-bg)] text-[var(--color-danger-text)]',
  neutral: 'bg-[var(--color-neutral-bg)] text-[var(--color-neutral-text)]',
  purple:  'bg-[var(--color-purple-bg)] text-[var(--color-purple-text)]',
};

export function Badge({
  variant = 'neutral',
  dot = false,
  children,
  className = '',
}: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1',
        'px-2 py-0.5 rounded-full',
        'text-xs font-semibold tracking-wide uppercase whitespace-nowrap',
        variantClasses[variant],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {dot && (
        <span
          aria-hidden="true"
          className="w-1.5 h-1.5 rounded-full bg-current flex-shrink-0"
        />
      )}
      {children}
    </span>
  );
}
