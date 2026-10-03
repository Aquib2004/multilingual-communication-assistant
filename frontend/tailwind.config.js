/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Explicit verification colours. Status must never be conveyed by
        // colour alone, so each of these is paired with an icon and a label.
        status: {
          pass: '#047857',
          warning: '#b45309',
          fail: '#b91c1c',
          review: '#1d4ed8',
          escalated: '#7e22ce',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
