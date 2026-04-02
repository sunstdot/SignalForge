import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TokenBurner ~ AI Intelligence Hub',
  description: 'Daily AI intelligence briefing with terminal aesthetic'
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="bg-terminal-bg min-h-screen text-terminal-text font-mono antialiased">
        {/* Grid background pattern */}
        <div className="fixed inset-0 bg-terminal-grid opacity-30 pointer-events-none" />
        
        {/* Main content */}
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}
