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

  /* ==========================================================================
     1. Ambient Cursor Spotlight Aura
     ========================================================================== */
  var spotlight = document.createElement('div');
  spotlight.id = 'ank-cursor-spotlight';
  spotlight.style.cssText = [
    'position: fixed',
    'top: 0',
    'left: 0',
    'width: 600px',
    'height: 600px',
    'margin-left: -300px',
    'margin-top: -300px',
    'border-radius: 50%',
    'pointer-events: none',
    'z-index: 1',
    'opacity: 0',
    'transition: opacity 600ms ease',
    'will-change: transform',
    'background: radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.05) 40%, transparent 70%)',
    'mix-blend-mode: screen',
  ].join(';');
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
    // Easing interpolation (lerp)
    spotX += (mouseX - spotX) * 0.12;
    spotY += (mouseY - spotY) * 0.12;
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
    'opacity: 0.7',
    'transition: opacity 800ms ease',
  ].join(';');

  // Insert before content so it stays behind UI elements
  document.body.insertBefore(canvas, document.body.firstChild);

  var ctx = canvas.getContext('2d');
  var width, height;
  var particles = [];
  var PARTICLE_COUNT = 48;
  var CONNECT_DISTANCE = 140;
  var MOUSE_RADIUS = 160;

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
    this.vx = (Math.random() - 0.5) * 0.6;
    this.vy = (Math.random() - 0.5) * 0.6;
    this.size = Math.random() * 2 + 1;
    this.baseX = this.x;
    this.baseY = this.y;
    this.density = Math.random() * 20 + 10;
  }

  Particle.prototype.update = function () {
    this.x += this.vx;
    this.y += this.vy;

    // Bounce off edges
    if (this.x < 0 || this.x > width) this.vx = -this.vx;
    if (this.y < 0 || this.y > height) this.vy = -this.vy;

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
      this.x -= directionX * 0.4;
      this.y -= directionY * 0.4;
    }
  };

  Particle.prototype.draw = function () {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    ctx.fillStyle = isDark ? 'rgba(165, 180, 252, 0.45)' : 'rgba(99, 102, 241, 0.35)';
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fill();
  };

  for (var i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
  }

  function renderParticles() {
    ctx.clearRect(0, 0, width, height);

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    for (var a = 0; a < particles.length; a++) {
      particles[a].update();
      particles[a].draw();

      for (var b = a + 1; b < particles.length; b++) {
        var dx = particles[a].x - particles[b].x;
        var dy = particles[a].y - particles[b].y;
        var dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < CONNECT_DISTANCE) {
          var opacity = (1 - dist / CONNECT_DISTANCE) * (isDark ? 0.18 : 0.1);
          ctx.strokeStyle = isDark ? 'rgba(129, 140, 248, ' + opacity + ')' : 'rgba(79, 70, 229, ' + opacity + ')';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(particles[a].x, particles[a].y);
          ctx.lineTo(particles[b].x, particles[b].y);
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(renderParticles);
  }
  requestAnimationFrame(renderParticles);

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

        // Set CSS variables for mouse-tracking border glow
        card.style.setProperty('--mouse-x', x + 'px');
        card.style.setProperty('--mouse-y', y + 'px');

        // 3D perspective tilt
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
