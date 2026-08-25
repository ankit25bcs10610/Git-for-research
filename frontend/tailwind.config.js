/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: '#3D81E3',
        lane: {
          1: '#22d3ee',
          2: '#a78bfa',
          3: '#fb923c',
          4: '#f472b6',
          5: '#4ade80',
          6: '#facc15',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
