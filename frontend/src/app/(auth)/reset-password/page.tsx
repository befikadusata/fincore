'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import axios from 'axios';
import { resetPasswordSchema } from '@/lib/schemas/auth';
import { Card, CardBody } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

type FieldErrors = Partial<Record<'password' | 'confirm_password', string>>;

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
      <path fillRule="evenodd" d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
    </svg>
  ) : (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path fillRule="evenodd" d="M3.28 2.22a.75.75 0 00-1.06 1.06l14.5 14.5a.75.75 0 101.06-1.06l-1.745-1.745a10.029 10.029 0 003.3-4.38 1.651 1.651 0 000-1.185A10.004 10.004 0 009.999 3a9.956 9.956 0 00-4.744 1.194L3.28 2.22zM7.752 6.69l1.092 1.092a2.5 2.5 0 013.374 3.373l1.091 1.092a4 4 0 00-5.557-5.557z" clipRule="evenodd" />
      <path d="M10.748 13.93l2.523 2.523a10.003 10.003 0 01-3.27.547c-4.258 0-7.894-2.66-9.337-6.41a1.651 1.651 0 010-1.186A10.007 10.007 0 012.839 6.02L6.07 9.252a4 4 0 004.678 4.678z" />
    </svg>
  );
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError('');
    setFieldErrors({});

    const result = resetPasswordSchema.safeParse({ password, confirm_password: confirm });
    if (!result.success) {
      const errs: FieldErrors = {};
      for (const issue of result.error.issues) {
        const key = issue.path[0] as keyof FieldErrors;
        if (key && !errs[key]) errs[key] = issue.message;
      }
      setFieldErrors(errs);
      return;
    }

    if (!token) {
      setApiError('Invalid or missing reset token. Please request a new reset link.');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/auth/password/reset/confirm/`,
        { token, password },
      );
      router.push('/login?reset=success');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const data = err.response?.data;
        setApiError(
          data?.detail ?? data?.token?.[0] ?? 'Failed to reset password. The link may have expired.',
        );
      } else {
        setApiError('Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <Card className="w-full max-w-[400px]">
        <CardBody className="p-8 text-center">
          <h2 className="text-xl font-semibold text-primary">Invalid reset link</h2>
          <p className="mt-2 text-sm text-secondary">
            This password reset link is missing or invalid. Please request a new one.
          </p>
          <Link
            href="/forgot-password"
            className="mt-6 inline-block text-sm font-medium text-brand hover:underline focus-visible:rounded focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)]"
          >
            Request new link
          </Link>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-[400px]">
      <CardBody className="p-8">
        <div className="mb-8 text-center">
          <span className="text-2xl font-bold tracking-tight text-primary">
            Fin<span className="text-brand">Core</span>
          </span>
          <h2 className="mt-3 text-lg font-semibold text-primary">Set new password</h2>
          <p className="mt-1 text-sm text-secondary">Choose a strong password for your account.</p>
        </div>

        {apiError && (
          <div
            role="alert"
            className="mb-5 rounded border border-[color:var(--color-danger-border)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger-text)]"
          >
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="password"
              className="text-sm font-medium text-primary after:ml-0.5 after:content-['*'] after:text-[var(--color-danger-text)]"
            >
              New password
            </label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                error={!!fieldErrors.password}
                aria-describedby={
                  fieldErrors.password ? 'password-error' : 'password-hint'
                }
                aria-invalid={!!fieldErrors.password}
                disabled={loading}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-tertiary hover:text-primary focus-visible:rounded focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)]"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                <EyeIcon open={showPassword} />
              </button>
            </div>
            {fieldErrors.password ? (
              <span id="password-error" className="text-sm text-[var(--color-danger-text)]">
                {fieldErrors.password}
              </span>
            ) : (
              <span id="password-hint" className="text-sm text-tertiary">
                Min. 8 characters
              </span>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="confirm"
              className="text-sm font-medium text-primary after:ml-0.5 after:content-['*'] after:text-[var(--color-danger-text)]"
            >
              Confirm new password
            </label>
            <div className="relative">
              <Input
                id="confirm"
                type={showConfirm ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="••••••••"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                error={!!fieldErrors.confirm_password}
                aria-describedby={fieldErrors.confirm_password ? 'confirm-error' : undefined}
                aria-invalid={!!fieldErrors.confirm_password}
                disabled={loading}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-tertiary hover:text-primary focus-visible:rounded focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)]"
                aria-label={showConfirm ? 'Hide confirm password' : 'Show confirm password'}
              >
                <EyeIcon open={showConfirm} />
              </button>
            </div>
            {fieldErrors.confirm_password && (
              <span id="confirm-error" className="text-sm text-[var(--color-danger-text)]">
                {fieldErrors.confirm_password}
              </span>
            )}
          </div>

          <Button type="submit" variant="primary" fullWidth loading={loading}>
            Reset password
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
