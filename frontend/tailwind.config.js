/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0a0f1e',
        'bg-secondary': '#1a2744',
        accent: '#e63946',
        neutral: '#f4f4f6',
        data: '#00b4d8',
      },
      fontFamily: {
        headline: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
