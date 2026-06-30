import { z } from 'zod';

export const loanCreateSchema = z.object({
  product: z.string().uuid('Invalid product ID'),
  borrower: z.string().uuid('Invalid borrower ID'),
  principal_amount: z
    .number({ error: 'Amount must be a number' })
    .positive('Principal amount must be greater than zero'),
  term_months: z
    .number({ error: 'Term must be a number' })
    .int({ message: 'Term must be a whole number' })
    .min(1, 'Term must be at least 1 month')
    .max(360, 'Term cannot exceed 360 months'),
  notes: z.string().max(2000, 'Notes must be 2000 characters or fewer').optional(),
  idempotency_key: z.string().uuid().optional(),
});

export const loanProductCreateSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  description: z.string().max(500).optional(),
  interest_type: z.enum(['FLAT', 'REDUCING_BALANCE']),
  interest_rate: z
    .number()
    .min(0, 'Interest rate cannot be negative')
    .max(100, 'Interest rate cannot exceed 100%'),
  compounding_periods_per_year: z.number().int().positive().optional(),
  min_term_months: z.number().int().positive(),
  max_term_months: z.number().int().positive(),
  min_amount: z.number().positive(),
  max_amount: z.number().positive(),
  currency: z.string().length(3).default('ETB'),
  fees_config: z.record(z.string(), z.unknown()).optional(),
  is_active: z.boolean().default(true),
}).refine((d) => d.max_term_months >= d.min_term_months, {
  message: 'max_term_months must be >= min_term_months',
  path: ['max_term_months'],
}).refine((d) => d.max_amount >= d.min_amount, {
  message: 'max_amount must be >= min_amount',
  path: ['max_amount'],
});

export type LoanCreate = z.infer<typeof loanCreateSchema>;
export type LoanProductCreate = z.infer<typeof loanProductCreateSchema>;
