import { formatAmount } from '@/lib/format';

type AmountSize = 'md' | 'lg' | 'xl' | '2xl' | '3xl';

interface AmountDisplayProps {
  amount: number;
  currency?: string;
  size?: AmountSize;
  className?: string;
}

const sizeClasses: Record<AmountSize, string> = {
  md:   'text-md',
  lg:   'text-lg',
  xl:   'text-xl',
  '2xl':'text-2xl',
  '3xl':'text-3xl',
};

export function AmountDisplay({
  amount,
  currency = 'ETB',
  size = 'md',
  className = '',
}: AmountDisplayProps) {
  return (
    <span
      className={[
        'font-mono font-semibold',
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {formatAmount(amount, currency)}
    </span>
  );
}
