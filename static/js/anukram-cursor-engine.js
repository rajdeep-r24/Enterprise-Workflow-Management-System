/**
 * Anukram Antigravity Cursor & Interactive Reactivity Engine
 * Provides cursor-following ambient spotlight, 3D card tilts,
 * magnetic interactions, and physics particle field.
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
     1. Ambient Cursor Spotlight Aura
     ========================================================================== */
  var spotlight = document.createElement('div');
  spotlight.id = 'ank-cursor-spotlight';
  spotlight.style.cssText = [
    'position: fixed',
    'top: 0',
    'left: 0',
    'width: 640px',
    'height: 640px',
    'margin-left: -320px',
    'margin-top: -320px',
    'border-radius: 50%',
    'pointer-events: none',
    'z-index: 1',
    'opacity: 0',
    'transition: opacity 500ms ease, background 500ms ease',
    'will-change: transform',
  ].join(';');

  function syncSpotlightTheme() {
    if (isDarkMode()) {
      spotlight.style.background = 'radial-gradient(circle, rgba(99, 102, 241, 0.26) 0%, rgba(147, 51, 234, 0.14) 40%, transparent 70%)';
      spotlight.style.mixBlendMode = 'screen';
    } else {
      // In light mode, normal blend mode with soft indigo-violet hue creates a visible luxurious glow
      spotlight.style.background = 'radial-gradient(circle, rgba(99, 102, 241, 0.22) 0%, rgba(139, 92, 246, 0.10) 45%, transparent 70%)';
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
    spotX += (mouseX - spotX) * 0.14;
    spotY += (mouseY - spotY) * 0.14;
    spotlight.style.transform = 'translate3d(' + spotX.toFixed(1) + 'px, ' + spotY.toFixed(1) + 'px, 0)';
    requestAnimationFrame(updateSpotlight);
  }
  requestAnimationFrame(updateSpotlight);

  /* ==========================================================================
     2. Interactive Particle Constellation Canvas (Antigravity Field)
     ========================================================================== */
  var canvas = document.createElement('canvas');
  canvas.id = 'ank-particle-canvas';
  canvas.style.cssText = [
    'position: fixed',
    'inset: 0',
    'width: 100%',
    'height: 100%',
    'pointer-events: none',
    'z-index: 0',
    'opacity: 0.85',
    'transition: opacity 800ms ease',
  ].join(';');

  document.body.insertBefore(canvas, document.body.firstChild);

  var ctx = canvas.getContext('2d');
  var width, height;
  var particles = [];
  var PARTICLE_COUNT = 60;
  var CONNECT_DISTANCE = 150;
  var MOUSE_RADIUS = 180;

  function resizeCanvas() {
    var dpr = window.devicePixelRatio || 1;
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function Particle() {
    this.x = Math.random() * width;
    this.y = Math.random() * height;
    this.vx = (Math.random() - 0.5) * 0.7;
    this.vy = (Math.random() - 0.5) * 0.7;
    this.size = Math.random() * 2.2 + 1.2;
    this.baseX = this.x;
    this.baseY = this.y;
    this.density = Math.random() * 25 + 12;
  }

  Particle.prototype.update = function () {
    this.x += this.vx;
    this.y += this.vy;

    // Wrap around screen edges for continuous flow
    if (this.x < -10) this.x = width + 10;
    if (this.x > width + 10) this.x = -10;
    if (this.y < -10) this.y = height + 10;
    if (this.y > height + 10) this.y = -10;

    // Mouse repulsion / antigravity reaction
    var dx = mouseX - this.x;
    var dy = mouseY - this.y;
    var distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < MOUSE_RADIUS && isMouseActive) {
      var forceDirectionX = dx / distance;
      var forceDirectionY = dy / distance;
      var maxDistance = MOUSE_RADIUS;
      var force = (maxDistance - distance) / maxDistance;
      var directionX = forceDirectionX * force * this.density;
      var directionY = forceDirectionY * force * this.density;
      this.x -= directionX * 0.45;
      this.y -= directionY * 0.45;
    }
  };

  Particle.prototype.draw = function () {
    var dark = isDarkMode();
    ctx.fillStyle = dark ? 'rgba(165, 180, 252, 0.85)' : 'rgba(79, 70, 229, 0.75)';
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fill();
  };

  for (var i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
  }

  function renderParticles() {
    ctx.clearRect(0, 0, width, height);
    var dark = isDarkMode();

    for (var a = 0; a < particles.length; a++) {
      particles[a].update();
      particles[a].draw();

      // Connect particle to nearby particles
      for (var b = a + 1; b < particles.length; b++) {
        var dx = particles[a].x - particles[b].x;
        var dy = particles[a].y - particles[b].y;
        var dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < CONNECT_DISTANCE) {
          var opacity = (1 - dist / CONNECT_DISTANCE) * (dark ? 0.28 : 0.22);
          ctx.strokeStyle = dark ? 'rgba(129, 140, 248, ' + opacity + ')' : 'rgba(99, 102, 241, ' + opacity + ')';
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(particles[a].x, particles[a].y);
          ctx.lineTo(particles[b].x, particles[b].y);
          ctx.stroke();
        }
      }

      // Connect particle directly to cursor if within range
      if (isMouseActive) {
        var mdx = mouseX - particles[a].x;
        var mdy = mouseY - particles[a].y;
        var mdist = Math.sqrt(mdx * mdx + mdy * mdy);
        if (mdist < 130) {
          var mOpacity = (1 - mdist / 130) * (dark ? 0.45 : 0.35);
          ctx.strokeStyle = dark ? 'rgba(56, 189, 248, ' + mOpacity + ')' : 'rgba(79, 70, 229, ' + mOpacity + ')';
          ctx.lineWidth = 1.4;
          ctx.beginPath();
          ctx.moveTo(particles[a].x, particles[a].y);
          ctx.lineTo(mouseX, mouseY);
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(renderParticles);
  }
  requestAnimationFrame(renderParticles);

  // Sync themes when user toggles dark/light mode
  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      if (m.attributeName === 'data-theme') {
        syncSpotlightTheme();
      }
    });
  });
  observer.observe(document.documentElement, { attributes: true });

  /* ==========================================================================
     3. 3D Card Gyro Tilt & Mouse-Following Spotlight Borders
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
        var rotateX = ((y - centerY) / centerY) * -5;
        var rotateY = ((x - centerX) / centerX) * 5;

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
     4. Magnetic Elements (Buttons & Eyebrows)
     ========================================================================== */
  function initMagneticElements() {
    var magnetics = document.querySelectorAll('.ff-btn--primary, .google-btn, .lp-hero__eyebrow');

    magnetics.forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var rect = el.getBoundingClientRect();
        var x = e.clientX - (rect.left + rect.width / 2);
        var y = e.clientY - (rect.top + rect.height / 2);

        el.style.transform = 'translate3d(' + (x * 0.18).toFixed(1) + 'px, ' + (y * 0.18).toFixed(1) + 'px, 0)';
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
