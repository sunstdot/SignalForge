import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TokenBurner - AI Intelligence Hub',
  description: 'Personal AI learning and experimentation system'
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
