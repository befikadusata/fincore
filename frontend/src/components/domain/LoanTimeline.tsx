import { LOAN_STATES, LOAN_TERMINAL_STATES } from '@/lib/status';

interface LoanTimelineProps {
  currentStatus: string;
}

const STATE_LABELS: Record<string, string> = {
  created:      'Created',
  submitted:    'Submitted',
  under_review: 'Under Review',
  approved:     'Approved',
  disbursed:    'Disbursed',
  active:       'Active',
  completed:    'Completed',
};

export function LoanTimeline({ currentStatus }: LoanTimelineProps) {
  const isTerminal = (LOAN_TERMINAL_STATES as readonly string[]).includes(currentStatus);
  const currentIdx = LOAN_STATES.indexOf(currentStatus as typeof LOAN_STATES[number]);

  return (
    <div className="flex items-start gap-0 overflow-x-auto pb-2" role="list" aria-label="Loan timeline">
      {LOAN_STATES.map((state, idx) => {
        const isCompleted = idx < currentIdx || (currentStatus === 'completed' && idx <= LOAN_STATES.length - 1);
        const isCurrent = state === currentStatus;
        const isPast = !isTerminal && idx < currentIdx;

        let dotClass = 'bg-[var(--color-neutral-rail)] border-[color:var(--color-neutral-border)]';
        let labelClass = 'text-tertiary';
        let lineClass = 'bg-[var(--color-border-default)]';

        if (isPast || isCompleted) {
          dotClass = 'bg-[var(--color-success-rail)] border-[color:var(--color-success-border)]';
          labelClass = 'text-[var(--color-success-text)]';
          lineClass = 'bg-[var(--color-success-rail)]';
        }

        if (isCurrent && !isTerminal) {
          dotClass = 'bg-brand border-brand';
          labelClass = 'text-brand-text font-semibold';
        }

        if (isTerminal && isCurrent) {
          dotClass = 'bg-[var(--color-danger-rail)] border-[color:var(--color-danger-border)]';
          labelClass = 'text-[var(--color-danger-text)] font-semibold';
        }

        return (
          <div
            key={state}
            role="listitem"
            className="flex flex-col items-center flex-1 min-w-[80px]"
          >
            <div className="flex items-center w-full">
              {idx > 0 && (
                <div className={`flex-1 h-0.5 ${isPast || isCompleted ? lineClass : 'bg-[var(--color-border-default)]'}`} />
              )}
              <div
                aria-current={isCurrent ? 'step' : undefined}
                className={[
                  'w-3 h-3 rounded-full border-2 flex-shrink-0',
                  dotClass,
                ].join(' ')}
              />
              {idx < LOAN_STATES.length - 1 && (
                <div className={`flex-1 h-0.5 ${isPast || isCompleted ? lineClass : 'bg-[var(--color-border-default)]'}`} />
              )}
            </div>
            <span className={`mt-1.5 text-xs text-center leading-tight ${labelClass}`}>
              {STATE_LABELS[state]}
            </span>
          </div>
        );
      })}

      {isTerminal && (
        <div className="flex flex-col items-center min-w-[80px]">
          <div className="flex items-center w-full">
            <div className="flex-1 h-0.5 bg-[var(--color-border-default)]" />
            <div className="w-3 h-3 rounded-full border-2 bg-[var(--color-danger-rail)] border-[color:var(--color-danger-border)] flex-shrink-0" />
          </div>
          <span className="mt-1.5 text-xs text-center leading-tight text-[var(--color-danger-text)] font-semibold">
            {currentStatus}
          </span>
        </div>
      )}
    </div>
  );
}
