'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { AmountDisplay } from '@/components/domain/AmountDisplay';
import { WalletDetailDrawer } from '@/components/finance/WalletDetailDrawer';
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

type WalletRailVariant = 'success' | 'warning' | 'neutral';

function walletStatusVariant(status: string): WalletRailVariant {
  if (status === 'ACTIVE') return 'success';
  if (status === 'FROZEN') return 'warning';
  return 'neutral';
}

export default function WalletsPage() {
  const [selectedWallet, setSelectedWallet] = useState<Wallet | null>(null);

  const { data: wallets = [], isLoading } = useQuery({
    queryKey: ['wallets'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/finance/wallets/');
      return (data?.results ?? data) as Wallet[];
    },
  });

  const walletTypeLabel = (type: string) =>
    type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Wallets</h1>
        <p className="text-sm text-secondary mt-1">View balances and transaction history</p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 bg-sunken animate-pulse rounded-lg" />
          ))}
        </div>
      ) : wallets.length === 0 ? (
        <EmptyState
          title="No wallets found"
          description="Wallets are created automatically when loans are disbursed."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {wallets.map((wallet) => (
            <button
              key={wallet.id}
              onClick={() => setSelectedWallet(wallet)}
              className="text-left focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-2 rounded-lg"
            >
              <Card
                statusRail={walletStatusVariant(wallet.status)}
                className="hover:border-[color:var(--color-border-strong)] transition-colors cursor-pointer h-full"
              >
                <div className="p-5 flex flex-col gap-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-primary">{wallet.owner_name}</p>
                      <p className="text-xs text-tertiary">{walletTypeLabel(wallet.wallet_type)}</p>
                    </div>
                    <Badge variant={walletStatusVariant(wallet.status)}>{wallet.status}</Badge>
                  </div>
                  <div>
                    <p className="text-xs text-tertiary mb-1">Balance</p>
                    <AmountDisplay amount={m(wallet.balance)} size="2xl" />
                    <p className="text-xs text-tertiary mt-0.5">{wallet.currency}</p>
                  </div>
                </div>
              </Card>
            </button>
          ))}
        </div>
      )}

      <WalletDetailDrawer
        open={!!selectedWallet}
        onClose={() => setSelectedWallet(null)}
        wallet={selectedWallet}
      />
    </div>
  );
}
