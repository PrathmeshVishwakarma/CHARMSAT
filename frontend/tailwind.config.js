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
          bg: "#060D08",
          card: "#0B1710",
          cardHover: "#102217",
          border: "#1E3A2B",
          borderGlow: "#4ADE80",
          neon: "#4ADE80",
          neonBright: "#5CFF7A",
          cyan: "#38BDF8",
          amber: "#FBBF24",
          red: "#F87171",
          muted: "#6B8E78",
          text: "#E2ECE5"
        }
      },
      fontFamily: {
        display: ['"Rajdhani"', '"Chakra Petch"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['"Inter"', 'sans-serif']
      },
      boxShadow: {
        neon: "0 0 15px rgba(74, 222, 128, 0.35)",
        neonGlow: "0 0 25px rgba(92, 255, 122, 0.5)",
        cyanGlow: "0 0 15px rgba(56, 189, 248, 0.35)",
        amberGlow: "0 0 15px rgba(251, 191, 36, 0.35)",
        redGlow: "0 0 15px rgba(248, 113, 113, 0.35)"
      }
    },
  },
  plugins: [],
}
