/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        green: {
          primary: '#1a6b3c',
          light: '#2d8a52',
          pale: '#e8f5ee',
        }
      }
    }
  },
  plugins: []
}
