import { Badge } from '@/components/ui/Badge';
import { loanStatusVariant } from '@/lib/status';

interface LoanStatusBadgeProps {
  status: string;
  dot?: boolean;
  className?: string;
}

export function LoanStatusBadge({ status, dot = false, className }: LoanStatusBadgeProps) {
  const variant = loanStatusVariant(status);
  const label = status.replace(/_/g, ' ');

  return (
    <Badge variant={variant} dot={dot} className={className}>
      {label}
    </Badge>
  );
}
