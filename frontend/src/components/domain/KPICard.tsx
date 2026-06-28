import { Card } from '@/components/ui/Card';
import { AmountDisplay } from './AmountDisplay';

interface KPICardProps {
  label: string;
  amount: number;
  currency?: string;
  delta?: {
    value: string;
    direction: 'up' | 'down' | 'neutral';
  };
}

export function KPICard({ label, amount, currency = 'ETB', delta }: KPICardProps) {
  const deltaColorClass =
    delta?.direction === 'up'
      ? 'text-[var(--color-success-text)]'
      : delta?.direction === 'down'
      ? 'text-[var(--color-warning-text)]'
      : 'text-tertiary';

  return (
    <Card>
      <div className="p-5 flex flex-col gap-1">
        <span className="text-sm text-secondary">{label}</span>
        <AmountDisplay amount={amount} currency={currency} size="3xl" />
        {delta && (
          <span className={`text-sm ${deltaColorClass}`}>{delta.value}</span>
        )}
      </div>
    </Card>
  );
}
