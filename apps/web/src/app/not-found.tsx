import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-terminal-bg">
      {/* Grid background */}
      <div className="fixed inset-0 bg-terminal-grid opacity-30 pointer-events-none" />
      
      <div className="relative z-10 terminal-window max-w-lg w-full">
        <div className="terminal-header">
          <div className="terminal-dot terminal-dot-red" />
          <div className="terminal-dot terminal-dot-yellow" />
          <div className="terminal-dot terminal-dot-green" />
          <span className="terminal-title">404_not_found</span>
        </div>
        
        <div className="terminal-content py-12 px-8 text-center">
          {/* ASCII Art Error */}
          <pre className="text-terminal-red text-xs sm:text-sm font-mono mb-6 overflow-x-auto">
{`
  ███████╗██████╗ ██████╗  ██████╗ ██████╗ 
  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝
  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗
  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
`}
          </pre>
          
          <div className="space-y-2 mb-8">
            <p className="text-terminal-lg font-semibold text-terminal-text">
              Page Not Found
            </p>
            <p className="text-terminal-sm text-terminal-text-muted">
              The requested resource could not be located
            </p>
          </div>

          {/* Terminal-style error details */}
          <div className="bg-terminal-bg-secondary rounded p-4 mb-8 text-left">
            <div className="text-terminal-xs text-terminal-text-muted font-mono space-y-1">
              <p><span className="text-terminal-red">ERROR:</span> Route not found</p>
              <p><span className="text-terminal-cyan">CODE:</span> 404</p>
              <p><span className="text-terminal-green">STATUS:</span> NOT_FOUND</p>
              <p><span className="text-terminal-yellow">TIMESTAMP:</span> {new Date().toISOString()}</p>
            </div>
          </div>

          <Link
            href="/"
            className="inline-flex items-center gap-2 text-terminal-cyan hover:text-terminal-green transition-colors duration-200 group"
          >
            <span className="text-lg group-hover:-translate-x-1 transition-transform">←</span>
            <span className="text-terminal-sm">Return to Home</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
