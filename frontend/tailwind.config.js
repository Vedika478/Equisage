/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        es: {
          bg: '#F1F2EC',
          panel: '#FFFFFF',
          brass: '#B6873A',
          'brass-deep': '#9C6F2A',
          sage: '#5C7857',
          gain: '#3F8F63',
          loss: '#B14631',
          text: '#1B2430',
          muted: '#6B7268'
        }
      },
      fontFamily: {
        display: ['"Instrument Serif"', 'serif'],
        body: ['"Work Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      borderColor: {
        'es-hairline': 'rgba(92, 120, 87, 0.2)'
      }
    },
  },
  plugins: [],
}
