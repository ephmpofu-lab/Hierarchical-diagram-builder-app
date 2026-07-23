(function () {
  const KEY = "diagram-builder-theme";

  function iconFor(theme) {
    return theme === "light" ? "☾" : "☀";
  }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("themeToggleBtn");
    if (!btn) return;
    const current = document.documentElement.dataset.theme === "light" ? "light" : "dark";
    btn.textContent = iconFor(current);
    btn.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
      localStorage.setItem(KEY, next);
      document.documentElement.dataset.theme = next;
      btn.textContent = iconFor(next);
    });
  });
})();
