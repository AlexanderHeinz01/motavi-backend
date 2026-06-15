/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Legacy app theme (analysis dashboard)
        'bg-primary': '#0a0f1e',
        'bg-secondary': '#1a2744',
        accent: '#e63946',
        neutral: '#f4f4f6',
        data: '#00b4d8',
        // Motavi brand design tokens (marketing + app redesign)
        brand: {
          DEFAULT: '#6C3AED',
          hover: '#5a2fd6',
          light: '#F5F3FF',
          subtle: 'rgba(108,58,237,0.12)',
        },
        ink: {
          DEFAULT: '#1A1A1A',
          secondary: '#6B7280',
          disabled: '#9CA3AF',
        },
        surface: '#F9FAFB',
        line: '#E5E7EB',
        dark: {
          DEFAULT: '#111111',
          mid: '#0a0a0f',
        },
        risk: {
          critical: '#ef4444',
          medium: '#f59e0b',
          low: '#22c55e',
        },
      },
      fontFamily: {
        // Legacy app
        headline: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['Inter', 'sans-serif'],
        // Motavi brand
        display: ['Outfit', 'sans-serif'],
        sans: ['Inter', 'sans-serif'],
      },
      borderRadius: {
        card: '10px',
      },
    },
  },
  plugins: [],
}
