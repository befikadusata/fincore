import { z } from 'zod';

export const repaymentSchema = z.object({
  amount: z
    .number({ error: 'Amount must be a number' })
    .positive('Payment amount must be greater than zero'),
  idempotency_key: z.string().uuid().optional(),
});

export type Repayment = z.infer<typeof repaymentSchema>;
