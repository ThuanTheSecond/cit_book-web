"use strict";
{
  window.addEventListener("load", function (e) {
    function setTheme(mode) {
      if (mode !== "light" && mode !== "dark" && mode !== "auto") {
        console.error(`Got invalid theme mode: ${mode}. Resetting to dark.`);
        mode = "dark"; // Default to dark instead of auto
      }
      document.documentElement.dataset.theme = mode;
      localStorage.setItem("theme", mode);
    }

    function cycleTheme() {
      const currentTheme = localStorage.getItem("theme") || "dark"; // Default to dark
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)"
      ).matches;

      if (prefersDark) {
        // Dark -> Light -> Auto
        if (currentTheme === "dark") {
          setTheme("light");
        } else if (currentTheme === "light") {
          setTheme("auto");
        } else {
          setTheme("dark");
        }
      } else {
        // Dark -> Light -> Auto
        if (currentTheme === "dark") {
          setTheme("light");
        } else if (currentTheme === "light") {
          setTheme("auto");
        } else {
          setTheme("dark");
        }
      }
    }

    function initTheme() {
      // Set dark theme as default
      const currentTheme = localStorage.getItem("theme") || "dark";
      setTheme(currentTheme);
    }

    function setupTheme() {
      // Attach event handlers for toggling themes
      const buttons = document.getElementsByClassName("theme-toggle");
      Array.from(buttons).forEach((btn) => {
        btn.addEventListener("click", cycleTheme);
      });
      initTheme();
    }

    setupTheme();
  });
}
