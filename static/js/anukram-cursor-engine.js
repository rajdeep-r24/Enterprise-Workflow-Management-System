/**
 * Anukram Precision Cursor & Interactive Reactivity Engine
 * Compact 280px ambient cursor spotlight, 3D card tilts,
 * magnetic interactions, and stationary blueprint dot matrix.
 */
(function () {
  'use strict';

  // Respect accessibility preferences
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  // Only enable on desktop pointer devices
  if (window.matchMedia('(pointer: coarse)').matches) {
    return;
  }

  function isDarkMode() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  /* ==========================================================================
     1. Compact & Focused Ambient Cursor Spotlight (280px)
     ========================================================================== */
  var spotlight = document.createElement('div');
  spotlight.id = 'ank-cursor-spotlight';
  spotlight.style.cssText = [
    'position: fixed',
    'top: 0',
    'left: 0',
    'width: 280px',
    'height: 280px',
    'margin-left: -140px',
    'margin-top: -140px',
    'border-radius: 50%',
    'pointer-events: none',
    'z-index: 1',
    'opacity: 0',
    'transition: opacity 400ms ease',
    'will-change: transform',
  ].join(';');

  function syncSpotlightTheme() {
    if (isDarkMode()) {
      spotlight.style.background = 'radial-gradient(circle, rgba(99, 102, 241, 0.20) 0%, rgba(147, 51, 234, 0.08) 50%, transparent 75%)';
      spotlight.style.mixBlendMode = 'screen';
    } else {
      spotlight.style.background = 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.05) 50%, transparent 75%)';
      spotlight.style.mixBlendMode = 'normal';
    }
  }
  syncSpotlightTheme();
  document.body.appendChild(spotlight);

  var mouseX = window.innerWidth / 2;
  var mouseY = window.innerHeight / 2;
  var spotX = mouseX;
  var spotY = mouseY;
  var isMouseActive = false;

  window.addEventListener('mousemove', function (e) {
    mouseX = e.clientX;
    mouseY = e.clientY;
    if (!isMouseActive) {
      isMouseActive = true;
      spotlight.style.opacity = '1';
    }
  }, { passive: true });

  window.addEventListener('mouseleave', function () {
    isMouseActive = false;
    spotlight.style.opacity = '0';
  });

  function updateSpotlight() {
    spotX += (mouseX - spotX) * 0.16;
    spotY += (mouseY - spotY) * 0.16;
    spotlight.style.transform = 'translate3d(' + spotX.toFixed(1) + 'px, ' + spotY.toFixed(1) + 'px, 0)';
    requestAnimationFrame(updateSpotlight);
  }
  requestAnimationFrame(updateSpotlight);

  // Sync theme changes
  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      if (m.attributeName === 'data-theme') {
        syncSpotlightTheme();
      }
    });
  });
  observer.observe(document.documentElement, { attributes: true });

  /* ==========================================================================
     2. 3D Card Gyro Tilt & Mouse-Following Spotlight Borders
     ========================================================================== */
  function initInteractiveCards() {
    var cards = document.querySelectorAll('.lp-feature, .lp-plan, .lp-testimonial, .lp-stat-card, .lp-card, .ff-card');

    cards.forEach(function (card) {
      card.classList.add('ank-interactive-card');

      card.addEventListener('mousemove', function (e) {
        var rect = card.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var y = e.clientY - rect.top;

        card.style.setProperty('--mouse-x', x + 'px');
        card.style.setProperty('--mouse-y', y + 'px');

        var centerX = rect.width / 2;
        var centerY = rect.height / 2;
        var rotateX = ((y - centerY) / centerY) * -4;
        var rotateY = ((x - centerX) / centerX) * 4;

        card.style.transform = 'perspective(1000px) rotateX(' + rotateX.toFixed(2) + 'deg) rotateY(' + rotateY.toFixed(2) + 'deg) translateY(-2px)';
        card.style.transition = 'transform 80ms ease-out';
      });

      card.addEventListener('mouseleave', function () {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0)';
        card.style.transition = 'transform 500ms cubic-bezier(0.2, 0.8, 0.2, 1)';
      });
    });
  }

  /* ==========================================================================
     3. Magnetic Elements (Buttons & Eyebrows)
     ========================================================================== */
  function initMagneticElements() {
    var magnetics = document.querySelectorAll('.ff-btn--primary, .google-btn, .lp-hero__eyebrow');

    magnetics.forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var rect = el.getBoundingClientRect();
        var x = e.clientX - (rect.left + rect.width / 2);
        var y = e.clientY - (rect.top + rect.height / 2);

        el.style.transform = 'translate3d(' + (x * 0.15).toFixed(1) + 'px, ' + (y * 0.15).toFixed(1) + 'px, 0)';
        el.style.transition = 'transform 60ms ease-out';
      });

      el.addEventListener('mouseleave', function () {
        el.style.transform = 'translate3d(0, 0, 0)';
        el.style.transition = 'transform 400ms cubic-bezier(0.34, 1.56, 0.64, 1)';
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initInteractiveCards();
      initMagneticElements();
    });
  } else {
    initInteractiveCards();
    initMagneticElements();
  }
})();
