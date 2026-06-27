(function () {
  const STORAGE_KEY = "cellusys-theme";
  const html = document.documentElement;

  var saved = localStorage.getItem(STORAGE_KEY);
  html.setAttribute("data-theme", saved || "light");

  window.__setTheme = function (theme) {
    html.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);
    if (typeof fetch !== "undefined") {
      fetch("/api/theme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme }),
      }).catch(function () {});
    }
  };

  window.__toggleTheme = function () {
    var current = html.getAttribute("data-theme") || "light";
    window.__setTheme(current === "dark" ? "light" : "dark");
  };
})();
