/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Custom accent color (can be overridden via CSS variables)
        accent: {
          50: 'var(--accent-50, #f0f9ff)',
          100: 'var(--accent-100, #e0f2fe)',
          200: 'var(--accent-200, #bae6fd)',
          300: 'var(--accent-300, #7dd3fc)',
          400: 'var(--accent-400, #38bdf8)',
          500: 'var(--accent-500, #0ea5e9)',
          600: 'var(--accent-600, #0284c7)',
          700: 'var(--accent-700, #0369a1)',
          800: 'var(--accent-800, #075985)',
          900: 'var(--accent-900, #0c4a6e)',
        },
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(-4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.2s ease-out',
      },
    },
  },
  plugins: [],
}

