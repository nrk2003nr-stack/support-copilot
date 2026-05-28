/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      animation: {
        'enter': 'enter 0.2s ease-out',
        'leave': 'leave 0.15s ease-in forwards',
      },
      keyframes: {
        enter: {
          '0%':   { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)',   opacity: '1' },
        },
        leave: {
          '0%':   { transform: 'scale(1)',   opacity: '1' },
          '100%': { transform: 'scale(0.9)', opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}
