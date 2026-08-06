(function () {
  "use strict";

  /* =========================================================
     Theme toggle
     ========================================================= */
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

  /* =========================================================
     Sidebar collapse / mobile toggle
     ========================================================= */
  function initSidebar() {
    var shell = document.querySelector(".ff-shell");
    if (!shell) return;

    var collapseBtn = document.querySelector("[data-sidebar-collapse]");

    var collapsed = localStorage.getItem("ff-sidebar-collapsed") === "1";
    if (collapsed) {
      shell.classList.add("is-collapsed");
      if (collapseBtn) collapseBtn.setAttribute("aria-expanded", "false");
    }

    if (collapseBtn) {
      collapseBtn.addEventListener("click", function () {
        shell.classList.toggle("is-collapsed");
        var isCollapsed = shell.classList.contains("is-collapsed");
        collapseBtn.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
        localStorage.setItem("ff-sidebar-collapsed", isCollapsed ? "1" : "0");
      });
    }

    document.querySelectorAll("[data-sidebar-mobile-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        shell.classList.toggle("is-mobile-open");
      });
    });

    // Close mobile sidebar when clicking outside
    document.addEventListener("click", function (e) {
      if (
        shell.classList.contains("is-mobile-open") &&
        !e.target.closest(".ff-sidebar") &&
        !e.target.closest("[data-sidebar-mobile-toggle]")
      ) {
        shell.classList.remove("is-mobile-open");
      }
    });
  }

  /* =========================================================
     Notification panel
     ========================================================= */
  function initNotifPanel() {
    var trigger = document.querySelector("[data-notif-trigger]");
    var panel = document.querySelector("[data-notif-panel]");
    if (!trigger || !panel) return;

    function openPanel() {
      panel.classList.add("is-open");
      panel.removeAttribute("aria-hidden");
      trigger.setAttribute("aria-expanded", "true");
    }

    function closePanel() {
      panel.classList.remove("is-open");
      panel.setAttribute("aria-hidden", "true");
      trigger.setAttribute("aria-expanded", "false");
    }

    trigger.addEventListener("click", function (e) {
      e.stopPropagation();
      if (panel.classList.contains("is-open")) {
        closePanel();
      } else {
        openPanel();
      }
    });

    document.addEventListener("click", function (e) {
      if (!panel.contains(e.target) && e.target !== trigger) {
        closePanel();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closePanel();
    });
  }

  /* =========================================================
     Auto-dismiss toasts (with hover pause)
     ========================================================= */
  function initToasts() {
    document.querySelectorAll(".ff-toast").forEach(function (toast) {
      var timeout;
      var DURATION = 5000;

      function startTimer() {
        timeout = setTimeout(function () {
          toast.style.transition = "opacity 220ms ease, transform 220ms ease";
          toast.style.opacity = "0";
          toast.style.transform = "translateX(8px)";
          setTimeout(function () { toast.remove(); }, 240);
        }, DURATION);
      }

      function clearTimer() { clearTimeout(timeout); }

      startTimer();
      toast.addEventListener("mouseenter", clearTimer);
      toast.addEventListener("mouseleave", startTimer);
    });
  }

  /* =========================================================
     Button loading state (data-loading-text)
     ========================================================= */
  function initLoadingButtons() {
    document.querySelectorAll("form").forEach(function (form) {
      form.addEventListener("submit", function () {
        var btn = form.querySelector("[type='submit']");
        if (btn && !btn.classList.contains("no-loading")) {
          btn.classList.add("is-loading");
          btn.disabled = true;
        }
      });
    });
  }

  /* =========================================================
     Init
     ========================================================= */
  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initSidebar();
    initNotifPanel();
    initToasts();
    initLoadingButtons();
  });
})();
