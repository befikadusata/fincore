import { Input } from './Input';

interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  /** col-amount | col-id | col-date | col-rate | col-count */
  colType?: 'amount' | 'id' | 'date' | 'rate' | 'count';
}

interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  /** Returns per-row CSS classes (e.g. status-rail-active) */
  rowClassName?: (row: T) => string;
  keyExtractor: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyState?: React.ReactNode;
}

const colTypeClasses: Record<NonNullable<Column<unknown>['colType']>, string> = {
  amount: 'font-mono text-right',
  id:     'font-mono text-sm text-secondary',
  date:   'font-mono text-sm text-secondary whitespace-nowrap',
  rate:   'font-mono text-right',
  count:  'font-mono text-right',
};

const colHeaderClasses: Record<NonNullable<Column<unknown>['colType']>, string> = {
  amount: 'text-right',
  id:     '',
  date:   '',
  rate:   'text-right',
  count:  'text-right',
};

export function Table<T>({
  columns,
  rows,
  rowClassName,
  keyExtractor,
  onRowClick,
  emptyState,
}: TableProps<T>) {
  return (
    <div className="overflow-x-auto border border-[color:var(--color-border-default)] rounded-lg">
      <table className="w-full border-collapse text-base">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={[
                  'px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest',
                  'text-tertiary bg-sunken border-b border-[color:var(--color-border-default)] whitespace-nowrap',
                  col.colType ? colHeaderClasses[col.colType] : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && emptyState ? (
            <tr>
              <td colSpan={columns.length}>{emptyState}</td>
            </tr>
          ) : (
            rows.map((row) => {
              const extraClass = rowClassName?.(row) ?? '';
              return (
                <tr
                  key={keyExtractor(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={[
                    'border-b border-[color:var(--color-border-default)] last:border-b-0',
                    'transition-colors duration-fast hover:bg-sunken',
                    onRowClick ? 'cursor-pointer' : '',
                    /* Status rail via box-shadow on first td — applied via className on the tr */
                    extraClass,
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {columns.map((col, idx) => (
                    <td
                      key={col.key}
                      className={[
                        'px-4 py-3 text-primary align-middle',
                        col.colType ? colTypeClasses[col.colType] : '',
                        /* Status rail: inset left shadow on the first cell */
                        idx === 0 && extraClass.includes('status-rail')
                          ? getRailShadow(extraClass)
                          : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

function getRailShadow(cls: string): string {
  if (cls.includes('status-rail-active'))  return 'shadow-[inset_3px_0_0_var(--color-success-rail)]';
  if (cls.includes('status-rail-overdue')) return 'shadow-[inset_3px_0_0_var(--color-warning-rail)]';
  if (cls.includes('status-rail-danger'))  return 'shadow-[inset_3px_0_0_var(--color-danger-rail)]';
  return '';
}

interface TableToolbarProps {
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (v: string) => void;
  children?: React.ReactNode;
}

export function TableToolbar({
  searchPlaceholder = 'Search…',
  searchValue = '',
  onSearchChange,
  children,
}: TableToolbarProps) {
  return (
    <div className="flex items-center gap-3 p-4 border-b border-[color:var(--color-border-default)] bg-surface flex-wrap">
      {onSearchChange && (
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-tertiary pointer-events-none">
            <SearchIcon />
          </span>
          <Input
            value={searchValue}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="pl-9"
          />
        </div>
      )}
      {children}
    </div>
  );
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
        clipRule="evenodd"
      />
    </svg>
  );
}
