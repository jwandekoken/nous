import { createApp } from "vue";

import router from "./router";
import App from "./App.vue";
import "./style.css";

const app = createApp(App);
app.use(router);

// Theme management based on system preference
const applyTheme = (isDark: boolean) => {
  if (isDark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
};

// Check system preference with fallback for older browsers
const getSystemThemePreference = (): boolean => {
  if (typeof window !== "undefined" && window.matchMedia) {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  // Fallback: default to light theme for older browsers
  return false;
};

// Apply initial theme
applyTheme(getSystemThemePreference());

// Listen for system preference changes (with browser support check)
if (typeof window !== "undefined" && window.matchMedia) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");

  // Use the modern addEventListener API if available, fallback to addListener
  if (prefersDark.addEventListener) {
    prefersDark.addEventListener("change", (e) => {
      applyTheme(e.matches);
    });
  } else {
    // Fallback for older Safari versions
    prefersDark.addListener((e) => {
      applyTheme(e.matches);
    });
  }
}

app.mount("#app");
