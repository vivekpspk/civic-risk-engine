/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pastel: {
          blue: '#E0F2FE',
          sky: '#BAE6FD',
          mint: '#D1FAE5',
          emerald: '#A7F3D0',
          lavender: '#EDE9FE',
          violet: '#DDD6FE',
          coral: '#FFE4E6',
          rose: '#FECDD3',
          amber: '#FEF3C7',
        }
      },
      fontFamily: {
        sans: ['Segoe UI', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(31, 38, 135, 0.07)',
        'glass-hover': '0 12px 40px 0 rgba(31, 38, 135, 0.12)',
      }
    },
  },
  plugins: [],
}
