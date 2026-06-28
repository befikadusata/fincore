'use client';

import { useState } from 'react';
import Link from 'next/link';
import axios from 'axios';
import { forgotPasswordSchema } from '@/lib/schemas/auth';
import { Card, CardBody } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [apiError, setApiError] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError('');
    setEmailError('');

    const result = forgotPasswordSchema.safeParse({ email });
    if (!result.success) {
      setEmailError(result.error.issues[0]?.message ?? 'Invalid email');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/auth/password/reset/`,
        { email },
      );
      setSubmitted(true);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status !== 404) {
        setApiError(
          err.response?.data?.detail ?? 'Failed to send reset email. Please try again.',
        );
      } else {
        setSubmitted(true);
      }
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <Card className="w-full max-w-[400px]">
        <CardBody className="p-8 text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-success-bg)]">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-6 w-6 text-[var(--color-success-text)]"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-primary">Check your email</h2>
          <p className="mt-2 text-sm text-secondary">
            If an account exists for{' '}
            <span className="font-medium text-primary">{email}</span>, you will receive
            a password reset link shortly.
          </p>
          <Link
            href="/login"
            className="mt-6 inline-block text-sm font-medium text-brand hover:underline focus-visible:rounded focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)]"
          >
            Back to sign in
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
          <h2 className="mt-3 text-lg font-semibold text-primary">Reset your password</h2>
          <p className="mt-1 text-sm text-secondary">
            Enter your email and we&apos;ll send you a reset link.
          </p>
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
              htmlFor="email"
              className="text-sm font-medium text-primary after:ml-0.5 after:content-['*'] after:text-[var(--color-danger-text)]"
            >
              Email address
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={!!emailError}
              aria-describedby={emailError ? 'email-error' : undefined}
              aria-invalid={!!emailError}
              disabled={loading}
            />
            {emailError && (
              <span id="email-error" className="text-sm text-[var(--color-danger-text)]">
                {emailError}
              </span>
            )}
          </div>

          <Button type="submit" variant="primary" fullWidth loading={loading}>
            Send reset link
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-secondary">
          Remember your password?{' '}
          <Link
            href="/login"
            className="font-medium text-brand hover:underline focus-visible:rounded focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)]"
          >
            Sign in
          </Link>
        </p>
      </CardBody>
    </Card>
  );
}
