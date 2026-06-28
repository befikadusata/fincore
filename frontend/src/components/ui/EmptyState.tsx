import { Button } from './Button';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center text-center px-8 py-16 gap-4">
      {icon && (
        <div className="w-12 h-12 text-disabled flex items-center justify-center">
          {icon}
        </div>
      )}
      <p className="text-xl font-semibold text-primary">{title}</p>
      {description && (
        <p className="text-base text-secondary max-w-[360px]">{description}</p>
      )}
      {action && (
        <Button variant="primary" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
