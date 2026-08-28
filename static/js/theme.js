(function () {
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("rollcall-theme", theme);
  }

  const saved = localStorage.getItem("rollcall-theme");
  if (!saved) {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(prefersDark ? "dark" : "light");
  } else {
    applyTheme(saved);
  }

  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
      if (!localStorage.getItem("rollcall-theme")) {
        applyTheme(e.matches ? "dark" : "light");
      }
    });
  }

  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-theme-toggle]");
    if (!btn) return;
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const next = isDark ? "light" : "dark";
    applyTheme(next);

    if (btn.dataset.authed === "true") {
      fetch("/api/toggle-theme", { method: "POST" }).catch(() => {});
    }
  });
})();