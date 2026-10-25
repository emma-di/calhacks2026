// The public demo build (VITE_HOSTED=1, GitHub Pages) has no receiver: it runs in Browser mode with
// test sounds only. Live microphones, names, questions and Claude need the laptop setup in the README.
export const HOSTED = import.meta.env?.VITE_HOSTED === "1";   // env is undefined under Node tests
export const REPO_URL = "https://github.com/emma-di/calhacks2026#try-it-on-your-laptop";
