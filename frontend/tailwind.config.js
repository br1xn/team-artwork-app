/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Outfit", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      colors: {
        moss: "#2E4036",
        clay: "#CC5833",
        cream: "#F2F0E9",
        charcoal: "#1A1A1A",
      },
      borderRadius: {
        instrument: "2rem",
        vault: "3rem",
      },
      boxShadow: {
        cinematic: "0 28px 90px rgba(13, 23, 18, 0.28)",
      },
    },
  },
  plugins: [],
};
