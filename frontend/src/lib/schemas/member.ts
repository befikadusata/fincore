import { z } from 'zod';

export const memberInviteSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Enter a valid email address')
    .max(254),
  role_id: z.string().uuid('Invalid role ID').optional(),
});

export type MemberInvite = z.infer<typeof memberInviteSchema>;
