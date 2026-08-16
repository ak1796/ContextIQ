import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Header } from '@/components/layout/Header';

/* ============================================================
   FONT LOADING — Inter & JetBrains Mono (Linear / Stripe spec)
   ============================================================ */
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
  title: 'ContextIQ — AI Context Compression & Guarded RAG Developer Console',
  description:
    'Production-grade Compressed Vector RAG, Token Budget Management & Grounding Verification Infrastructure',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} dark`}
    >
      <body className="min-h-screen flex flex-col font-sans bg-[color:var(--background)] text-[color:var(--foreground)]">
        <Header />
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
