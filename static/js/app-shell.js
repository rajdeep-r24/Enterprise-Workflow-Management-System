(function () {
  "use strict";

  // ---- Theme toggle -------------------------------------------------
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    document.querySelectorAll("[data-theme-toggle] i").forEach(function (icon) {
      icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
    });
  }

  function initTheme() {
    var stored = localStorage.getItem("ff-theme");
    applyTheme(stored || document.documentElement.getAttribute("data-theme") || "light");

    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var current = document.documentElement.getAttribute("data-theme");
        var next = current === "dark" ? "light" : "dark";
        localStorage.setItem("ff-theme", next);
        applyTheme(next);
      });
    });
  }

  // ---- Sidebar collapse / mobile toggle ------------------------------
  function initSidebar() {
    var shell = document.querySelector(".ff-shell");
    if (!shell) return;

    var collapsed = localStorage.getItem("ff-sidebar-collapsed") === "1";
    if (collapsed) shell.classList.add("is-collapsed");

    document.querySelectorAll("[data-sidebar-collapse]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        shell.classList.toggle("is-collapsed");
        localStorage.setItem(
          "ff-sidebar-collapsed",
          shell.classList.contains("is-collapsed") ? "1" : "0"
        );
      });
    });

    document.querySelectorAll("[data-sidebar-mobile-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        shell.classList.toggle("is-mobile-open");
      });
    });
  }

  // ---- Notification panel toggle -------------------------------------
  function initNotifPanel() {
    var trigger = document.querySelector("[data-notif-trigger]");
    var panel = document.querySelector("[data-notif-panel]");
    if (!trigger || !panel) return;

    trigger.addEventListener("click", function (e) {
      e.stopPropagation();
      panel.style.display = panel.style.display === "block" ? "none" : "block";
    });

    document.addEventListener("click", function (e) {
      if (!panel.contains(e.target) && e.target !== trigger) {
        panel.style.display = "none";
      }
    });
  }

  // ---- Auto-dismiss toasts --------------------------------------------
  function initToasts() {
    document.querySelectorAll(".ff-toast").forEach(function (toast) {
      setTimeout(function () {
        toast.style.transition = "opacity 200ms";
        toast.style.opacity = "0";
        setTimeout(function () { toast.remove(); }, 200);
      }, 5000);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initSidebar();
    initNotifPanel();
    initToasts();
  });
})();
