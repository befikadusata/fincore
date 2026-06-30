export type BadgeVariant = 'success' | 'info' | 'warning' | 'danger' | 'neutral' | 'purple';

const LOAN_STATUS_MAP: Record<string, BadgeVariant> = {
  created:      'neutral',
  submitted:    'info',
  under_review: 'purple',
  approved:     'success',
  disbursed:    'success',
  active:       'success',
  completed:    'neutral',
  rejected:     'danger',
  defaulted:    'danger',
  overdue:      'warning',
};

export function loanStatusVariant(status: string): BadgeVariant {
  return LOAN_STATUS_MAP[status] ?? 'neutral';
}

/** Maps a loan status to the CSS class suffix for status rails on table rows. */
export function loanStatusRailClass(status: string): string {
  const variant = loanStatusVariant(status);
  const railMap: Record<BadgeVariant, string> = {
    success: 'status-rail-active',
    warning: 'status-rail-overdue',
    danger:  'status-rail-danger',
    info:    '',
    neutral: '',
    purple:  '',
  };
  return railMap[variant];
}

/** Ordered loan state machine steps for LoanTimeline. */
export const LOAN_STATES = [
  'created',
  'submitted',
  'under_review',
  'approved',
  'disbursed',
  'active',
  'completed',
] as const;

export const LOAN_TERMINAL_STATES = ['rejected', 'defaulted'] as const;
