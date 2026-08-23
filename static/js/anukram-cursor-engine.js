/**
 * Anukram Precision Cursor & Interactive Reactivity Engine
 * Provides subtle 3D card perspective tilts and magnetic button interactions.
 * (No mouse spotlight circles or particle distractions).
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

  /* ==========================================================================
     1. 3D Card Gyro Tilt & Mouse-Following Spotlight Borders
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
     2. Magnetic Elements (Buttons & Eyebrows)
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
