import type { BadgeVariant } from '@/lib/status';

type StatusRailVariant = Extract<BadgeVariant, 'success' | 'warning' | 'danger' | 'purple' | 'neutral'>;

interface CardProps {
  statusRail?: StatusRailVariant;
  className?: string;
  children: React.ReactNode;
}

const railClasses: Record<StatusRailVariant, string> = {
  success: 'before:bg-[var(--color-success-rail)]',
  warning: 'before:bg-[var(--color-warning-rail)]',
  danger:  'before:bg-[var(--color-danger-rail)]',
  purple:  'before:bg-[var(--color-purple-rail)]',
  neutral: 'before:bg-[var(--color-neutral-rail)]',
};

export function Card({ statusRail, className = '', children }: CardProps) {
  const hasRail = statusRail !== undefined;

  return (
    <div
      className={[
        'bg-surface border border-[color:var(--color-border-default)] rounded-lg shadow-sm overflow-hidden',
        hasRail
          ? [
              'flex',
              'before:content-[""] before:flex-shrink-0 before:w-[3px] before:self-stretch',
              'before:rounded-l-sm',
              railClasses[statusRail],
            ].join(' ')
          : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {hasRail ? <div className="flex-1 min-w-0">{children}</div> : children}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  actions?: React.ReactNode;
  className?: string;
}

export function CardHeader({ title, actions, className = '' }: CardHeaderProps) {
  return (
    <div
      className={[
        'flex items-center justify-between px-5 py-4',
        'border-b border-[color:var(--color-border-default)]',
        className,
      ].join(' ')}
    >
      <h2 className="text-xl font-semibold text-primary">{title}</h2>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}

export function CardBody({
  className = '',
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

export function CardFooter({
  className = '',
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={[
        'px-5 py-4 flex items-center justify-end gap-3',
        'border-t border-[color:var(--color-border-default)] bg-sunken',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  );
}
