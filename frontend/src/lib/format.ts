/** Formats a minor-unit integer (e.g. cents) to a currency string. */
export function formatAmount(
  amount: number,
  currency = 'ETB',
  locale = 'en-ET'
): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      currencyDisplay: 'code',
      minimumFractionDigits: 2,
    }).format(amount / 100);
  } catch {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      currencyDisplay: 'code',
      minimumFractionDigits: 2,
    }).format(amount / 100);
  }
}

/** Formats a UUID to a short loan ID: LN-XXXXXXXX */
export function formatLoanId(id: string): string {
  return `LN-${id.replace(/-/g, '').slice(0, 8).toUpperCase()}`;
}

/** Formats an ISO date string to "DD Mon YYYY" e.g. "28 Jun 2026". */
export function formatDate(date: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(date));
}

/** Returns a human-readable elapsed time string (e.g. "2h ago", "3d ago"). */
export function formatElapsed(date: string | Date): string {
  const ms = Date.now() - new Date(date).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
