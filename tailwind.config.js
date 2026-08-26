/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                accu: {
                    50: '#f0f8ff',
                    100: '#e0f0fe',
                    200: '#bae2fd',
                    300: '#7ccbfd',
                    400: '#4a90d9',
                    500: '#2479C2', // Official AccuDesign Primary Brand Blue
                    600: '#1a5fa0', // AccuDesign Deep/Hover Blue
                    700: '#1a5db0',
                    800: '#1e3a8a',
                    900: '#0f172a',
                    950: '#0b1329',
                },
                accuorange: {
                    400: '#ff8a5b',
                    500: '#f1683a', // AccuDesign Orange Accent / CTA
                    600: '#ea580c',
                }
            },
            fontFamily: {
                sans: ['Poppins', 'Inter', 'sans-serif'],
                heading: ['Poppins', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            }
        },
    },
    plugins: [],
}
