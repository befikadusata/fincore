'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Drawer } from '@/components/ui/Drawer';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { AmountDisplay } from '@/components/domain/AmountDisplay';
import { formatDate, formatAmount } from '@/lib/format';
import api from '@/lib/api';

const m = (v: string | number | null | undefined) =>
  Math.round(parseFloat(String(v ?? 0)) * 100);

interface Wallet {
  id: string;
  owner_name: string;
  wallet_type: string;
  currency: string;
  balance: string;
  status: string;
  created_at: string;
}

interface StatementEntry {
  id: string;
  created_at: string;
  entry_type: 'CREDIT' | 'DEBIT';
  amount: string;
  reference: string;
  description: string;
  balance_after: string;
}

interface StatementData {
  wallet_id: string;
  currency: string;
  opening_balance: string;
  closing_balance: string;
  entries: StatementEntry[];
}

interface WalletDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  wallet: Wallet | null;
}

export function WalletDetailDrawer({ open, onClose, wallet }: WalletDetailDrawerProps) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const params = new URLSearchParams();
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);

  const { data: statement, isFetching } = useQuery({
    queryKey: ['wallet-statement', wallet?.id, startDate, endDate],
    queryFn: async () => {
      const qs = params.toString();
      const { data } = await api.get<StatementData>(
        `/api/v1/finance/wallets/${wallet!.id}/statement/${qs ? `?${qs}` : ''}`
      );
      return data;
    },
    enabled: open && !!wallet?.id,
  });

  if (!wallet) return null;

  const walletTypeLabel = wallet.wallet_type
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <Drawer open={open} onClose={onClose} title={`${walletTypeLabel} Wallet`}>
      <div className="flex flex-col gap-6">
        {/* Wallet summary */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-secondary">{wallet.owner_name}</span>
            <Badge variant={wallet.status === 'ACTIVE' ? 'success' : wallet.status === 'FROZEN' ? 'warning' : 'neutral'}>
              {wallet.status}
            </Badge>
          </div>

          <div className="bg-sunken rounded-xl px-5 py-4 text-center">
            <p className="text-xs text-tertiary mb-1">Current balance</p>
            <AmountDisplay amount={m(wallet.balance)} size="3xl" />
            <p className="text-xs text-tertiary mt-1">{wallet.currency}</p>
          </div>
        </div>

        {/* Date range filter */}
        <div>
          <p className="text-sm font-medium text-primary mb-3">Statement</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-secondary">From</label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-secondary">To</label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>
        </div>

        {/* Summary balances */}
        {statement && (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-sunken rounded-lg px-3 py-2.5">
              <p className="text-xs text-tertiary">Opening</p>
              <p className="font-mono font-semibold text-sm text-primary mt-0.5">
                {formatAmount(m(statement.opening_balance))}
              </p>
            </div>
            <div className="bg-sunken rounded-lg px-3 py-2.5">
              <p className="text-xs text-tertiary">Closing</p>
              <p className="font-mono font-semibold text-sm text-primary mt-0.5">
                {formatAmount(m(statement.closing_balance))}
              </p>
            </div>
          </div>
        )}

        {/* Transactions list */}
        {isFetching ? (
          <p className="text-sm text-tertiary text-center py-6">Loading…</p>
        ) : !statement?.entries?.length ? (
          <p className="text-sm text-tertiary text-center py-6">No transactions in this period.</p>
        ) : (
          <div className="flex flex-col divide-y divide-[color:var(--color-border-default)]">
            {statement.entries.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between py-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-primary truncate">{entry.description || entry.reference || '—'}</p>
                  <p className="text-xs font-mono text-tertiary mt-0.5">{formatDate(entry.created_at)}</p>
                </div>
                <div className="text-right ml-4 flex-shrink-0">
                  <p
                    className={[
                      'font-mono font-semibold text-sm',
                      entry.entry_type === 'CREDIT'
                        ? 'text-[var(--color-success-text)]'
                        : 'text-[var(--color-danger-text)]',
                    ].join(' ')}
                  >
                    {entry.entry_type === 'CREDIT' ? '+' : '-'}
                    {formatAmount(m(entry.amount))}
                  </p>
                  <p className="text-xs font-mono text-tertiary">
                    Bal: {formatAmount(m(entry.balance_after))}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Drawer>
  );
}
