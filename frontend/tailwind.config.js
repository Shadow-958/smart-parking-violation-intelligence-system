/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        asphalt: {
          DEFAULT: "#23262B",
          light: "#2E3238",
          dark: "#17191D",
        },
        paper: "#F5F5F1",
        ink: "#1A1A1A",
        curb: {
          red: "#C8102E",
          yellow: "#F2B705",
          green: "#1B7A43",
          blue: "#2B4C7E",
        },
      },
      fontFamily: {
        display: ["Oswald", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
