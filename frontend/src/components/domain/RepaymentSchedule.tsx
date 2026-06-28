import { Table } from '@/components/ui/Table';
import { formatDate } from '@/lib/format';
import { AmountDisplay } from './AmountDisplay';
import { LoanStatusBadge } from './LoanStatusBadge';

export interface Installment {
  id: string;
  installment_number: number;
  due_date: string;
  principal_amount: number;
  interest_amount: number;
  total_amount: number;
  penalty_amount?: number;
  status: string;
}

interface RepaymentScheduleProps {
  installments: Installment[];
}

export function RepaymentSchedule({ installments }: RepaymentScheduleProps) {
  return (
    <Table
      keyExtractor={(row) => row.id}
      rows={installments}
      columns={[
        {
          key: 'number',
          header: '#',
          colType: 'count',
          render: (row) => <span className="font-mono text-sm text-secondary">{row.installment_number}</span>,
        },
        {
          key: 'due_date',
          header: 'Due Date',
          colType: 'date',
          render: (row) => formatDate(row.due_date),
        },
        {
          key: 'principal',
          header: 'Principal',
          colType: 'amount',
          render: (row) => <AmountDisplay amount={row.principal_amount} />,
        },
        {
          key: 'interest',
          header: 'Interest',
          colType: 'amount',
          render: (row) => <AmountDisplay amount={row.interest_amount} />,
        },
        {
          key: 'total',
          header: 'Total',
          colType: 'amount',
          render: (row) => <AmountDisplay amount={row.total_amount} />,
        },
        {
          key: 'status',
          header: 'Status',
          render: (row) => <LoanStatusBadge status={row.status} />,
        },
      ]}
    />
  );
}
