import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { THEME_SCRIPT } from '@/lib/theme';
import Providers from './providers';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: { template: '%s — FinCore', default: 'FinCore' },
  description: 'Multi-tenant lending management platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        {/* Apply saved theme before first paint — prevents flash */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-page text-primary antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
