import { z } from 'zod';

export const roleCreateSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  slug: z
    .string()
    .min(1)
    .max(100)
    .regex(/^[a-z0-9-]+$/, 'Slug may only contain lowercase letters, numbers, and hyphens')
    .optional(),
  permission_ids: z.array(z.string().uuid()).default([]),
});

export const assignPermissionsSchema = z.object({
  permission_ids: z.array(z.string().uuid()).min(0),
});

export type RoleCreate = z.infer<typeof roleCreateSchema>;
export type AssignPermissions = z.infer<typeof assignPermissionsSchema>;
