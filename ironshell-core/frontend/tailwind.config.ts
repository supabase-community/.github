import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // IronShell brand colors
        'iron': {
          50: '#f6f7f9',
          100: '#eceef2',
          200: '#d5dae3',
          300: '#b1bbca',
          400: '#8796ac',
          500: '#687992',
          600: '#536179',
          700: '#444f62',
          800: '#3b4453',
          900: '#343b47',
          950: '#22262f',
        },
        // Accent colors for UI states
        'success': {
          50: '#f0fdf4',
          500: '#22c55e',
          600: '#16a34a',
        },
        'warning': {
          50: '#fffbeb',
          500: '#f59e0b',
          600: '#d97706',
        },
        'danger': {
          50: '#fef2f2',
          500: '#ef4444',
          600: '#dc2626',
        },
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

export default config
