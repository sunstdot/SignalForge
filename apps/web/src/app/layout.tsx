import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TokenBurner - AI Intelligence Hub',
  description: 'Daily AI intelligence briefing'
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
