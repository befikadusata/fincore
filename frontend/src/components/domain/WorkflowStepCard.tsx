import { Button } from '@/components/ui/Button';
import { formatLoanId, formatElapsed } from '@/lib/format';
import { AmountDisplay } from './AmountDisplay';

export interface WorkflowStep {
  id: string;
  entity_id: string;
  borrower_name: string;
  amount: number;
  loan_term_months?: number;
  step_type: string;
  submitted_at: string;
  is_read?: boolean;
}

interface WorkflowStepCardProps {
  step: WorkflowStep;
  onReview: (step: WorkflowStep) => void;
}

export function WorkflowStepCard({ step, onReview }: WorkflowStepCardProps) {
  const stepLabel =
    step.step_type === 'approval'
      ? 'Loan Approval'
      : step.step_type.charAt(0).toUpperCase() + step.step_type.slice(1);

  return (
    <div className="flex items-start gap-3 px-4 py-4 border-b border-[color:var(--color-border-default)] last:border-b-0 hover:bg-sunken transition-colors duration-fast">
      {/* Unread dot */}
      <div className="mt-1.5 w-2 h-2 flex-shrink-0">
        {!step.is_read && (
          <span
            aria-label="Unread"
            className="block w-2 h-2 rounded-full bg-brand"
          />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-semibold text-primary">{stepLabel}</span>
          <span className="font-mono text-sm text-secondary">
            {formatLoanId(step.entity_id)}
          </span>
          <span className="text-sm text-primary">{step.borrower_name}</span>
        </div>
        <div className="flex items-center gap-2 mt-1 text-sm text-secondary flex-wrap">
          <AmountDisplay amount={step.amount} />
          {step.loan_term_months && (
            <>
              <span>·</span>
              <span className="font-mono">{step.loan_term_months} months</span>
            </>
          )}
          <span>·</span>
          <span className="font-mono text-xs">{formatElapsed(step.submitted_at)}</span>
        </div>
      </div>

      <Button
        variant="secondary"
        size="sm"
        onClick={() => onReview(step)}
        className="flex-shrink-0"
      >
        Review
      </Button>
    </div>
  );
}
