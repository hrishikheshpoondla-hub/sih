/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          dark: '#0a0d14',
          darker: '#06080d',
          card: '#101522',
          border: '#1e293b',
          accent: '#00f2fe',
          neonGreen: '#10b981',
          neonAmber: '#f59e0b',
          neonRed: '#ef4444',
          neonPurple: '#a855f7'
        }
      }
    },
  },
  plugins: [],
}
