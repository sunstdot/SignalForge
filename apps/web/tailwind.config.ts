import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}'
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0d1117',
          'bg-secondary': '#161b22',
          'bg-tertiary': '#21262d',
          border: '#30363d',
          'border-light': '#484f58',
          text: '#e6edf3',
          'text-muted': '#7d8590',
          'text-dim': '#484f58',
          cyan: '#39d0d8',
          green: '#7ee787',
          blue: '#58a6ff',
          yellow: '#d29922',
          red: '#f85149',
          purple: '#a371f7',
          orange: '#ff7b72'
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Source Code Pro', 'ui-monospace', 'monospace'],
        display: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace']
      },
      fontSize: {
        'terminal-xs': ['0.75rem', { lineHeight: '1.5' }],
        'terminal-sm': ['0.8125rem', { lineHeight: '1.6' }],
        'terminal-base': ['0.875rem', { lineHeight: '1.7' }],
        'terminal-lg': ['1rem', { lineHeight: '1.6' }]
      },
      spacing: {
        'terminal': '1.5rem',
        'terminal-sm': '0.75rem',
        'terminal-xs': '0.5rem'
      },
      animation: {
        'cursor-blink': 'blink 1s step-end infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in': 'slideIn 0.2s ease-out'
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' }
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideIn: {
          '0%': { transform: 'translateX(-10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' }
        }
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(to right, #21262d 1px, transparent 1px), linear-gradient(to bottom, #21262d 1px, transparent 1px)',
        'dots-pattern': 'radial-gradient(circle, #30363d 1px, transparent 1px)'
      },
      boxShadow: {
        'terminal': '0 0 0 1px #30363d, 0 4px 6px -1px rgba(0, 0, 0, 0.3)',
        'terminal-glow': '0 0 20px rgba(57, 208, 216, 0.1)',
        'glow-cyan': '0 0 10px rgba(57, 208, 216, 0.3)',
        'glow-green': '0 0 10px rgba(126, 231, 135, 0.3)'
      }
    }
  },
  plugins: [
    function ({ addUtilities }: { addUtilities: Function }) {
      addUtilities({
        '.scrollbar-terminal': {
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px'
          },
          '&::-webkit-scrollbar-track': {
            background: '#161b22'
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#30363d',
            borderRadius: '4px'
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#484f58'
          }
        },
        '.text-glow-cyan': {
          textShadow: '0 0 10px rgba(57, 208, 216, 0.5)'
        },
        '.text-glow-green': {
          textShadow: '0 0 10px rgba(126, 231, 135, 0.5)'
        }
      });
    }
  ]
};

export default config;
