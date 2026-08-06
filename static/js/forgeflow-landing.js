/* ==========================================================================
   ForgeFlow Landing — Animation Engine v3
   Signature: The Approval Transit
   ========================================================================== */
(function () {
  'use strict';

  /* =========================================================
     Utilities
     ========================================================= */
  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return (ctx || document).querySelectorAll(sel); }
  function delay(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  /* =========================================================
     1. Section reveal — IntersectionObserver
     ========================================================= */
  function initReveal() {
    if (!('IntersectionObserver' in window)) {
      qsa('[data-reveal]').forEach(function (el) { el.classList.add('is-revealed'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('is-revealed'); io.unobserve(e.target); }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });
    qsa('[data-reveal]').forEach(function (el) { io.observe(el); });
  }

  /* =========================================================
     2. KPI counters
     ========================================================= */
  function initCounters() {
    if (!('IntersectionObserver' in window)) return;
    function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
    function run(el) {
      var target = parseInt(el.getAttribute('data-counter'), 10);
      var suffix = el.getAttribute('data-suffix') || '';
      var start = null;
      var dur = 1600;
      requestAnimationFrame(function step(ts) {
        if (!start) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        el.textContent = Math.round(easeOut(p) * target).toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(step);
      });
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { run(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.6 });
    qsa('[data-counter]').forEach(function (el) { io.observe(el); });
  }

  /* =========================================================
     3. Hero simulation — cinematic state machine
     Cycles through: SUBMITTED → ROUTING → IT_APPROVED →
                     HR_ROUTING → HR_APPROVED → ISSUED → RESET
     ========================================================= */
  var HERO_STATES = [
    { id: 'submitted',   label: 'Submitted',       badge: 'accent',   icon: 'bi-file-earmark-plus', ms: 1800 },
    { id: 'routing',     label: 'Routing…',         badge: 'warning',  icon: 'bi-signpost-split',    ms: 1600 },
    { id: 'it-review',   label: 'IT Head Review',   badge: 'warning',  icon: 'bi-hourglass-split',   ms: 2000 },
    { id: 'it-approved', label: 'IT Approved ✓',    badge: 'success',  icon: 'bi-check-circle-fill', ms: 1400 },
    { id: 'hr-review',   label: 'HR Review',        badge: 'warning',  icon: 'bi-hourglass-split',   ms: 2000 },
    { id: 'hr-approved', label: 'HR Approved ✓',    badge: 'success',  icon: 'bi-check-circle-fill', ms: 1400 },
    { id: 'issued',      label: 'QR Slip Issued',   badge: 'success',  icon: 'bi-patch-check-fill',  ms: 2400 },
  ];

  function initHeroSim() {
    var sim = qs('#hero-sim');
    if (!sim) return;

    var progressBar   = qs('#sim-progress');
    var stateLabel    = qs('#sim-state-label');
    var stepDots      = qsa('.sim-dot', sim);
    var requestCard   = qs('#sim-request-card');
    var notifStack    = qs('#sim-notif-stack');
    var qrReveal      = qs('#sim-qr');

    var current = 0;
    var running = true;

    function setProgress(pct) {
      if (progressBar) progressBar.style.width = pct + '%';
    }

    function showNotif(text, type) {
      if (!notifStack) return;
      var n = document.createElement('div');
      n.className = 'sim-notif sim-notif--' + type;
      n.innerHTML = '<i class="bi bi-bell-fill"></i><span>' + text + '</span>';
      notifStack.prepend(n);
      requestAnimationFrame(function () { n.classList.add('is-in'); });
      setTimeout(function () {
        n.classList.remove('is-in');
        setTimeout(function () { if (n.parentNode) n.parentNode.removeChild(n); }, 400);
      }, 3200);
    }

    function activateDot(idx) {
      stepDots.forEach(function (d, i) {
        d.classList.toggle('is-active', i === idx);
        d.classList.toggle('is-done', i < idx);
      });
    }

    var stateActions = {
      'submitted':   function () { setProgress(8);  activateDot(0); if (requestCard) { requestCard.classList.remove('is-hidden'); requestCard.classList.add('is-in'); } },
      'routing':     function () { setProgress(25); activateDot(1); showNotif('Routing to IT Head…', 'info'); },
      'it-review':   function () { setProgress(42); activateDot(2); showNotif('Rohan Mehta reviewing', 'warning'); },
      'it-approved': function () { setProgress(58); activateDot(3); showNotif('IT Head approved', 'success'); if (requestCard) { var b = requestCard.querySelector('.sim-card__badge'); if (b) b.textContent = '1/2 Approved'; } },
      'hr-review':   function () { setProgress(72); activateDot(4); showNotif('HR Director reviewing', 'warning'); },
      'hr-approved': function () { setProgress(88); activateDot(5); showNotif('HR Director approved', 'success'); },
      'issued':      function () { setProgress(100); activateDot(6); if (qrReveal) qrReveal.classList.add('is-in'); showNotif('QR slip emailed to Priya', 'success'); }
    };

    async function runLoop() {
      while (running) {
        for (var i = 0; i < HERO_STATES.length; i++) {
          var state = HERO_STATES[i];
          if (stateLabel) stateLabel.textContent = state.label;
          var action = stateActions[state.id];
          if (action) action();
          await delay(state.ms);
        }
        // Reset
        setProgress(0);
        activateDot(-1);
        if (requestCard) { requestCard.classList.remove('is-in'); }
        if (qrReveal)    { qrReveal.classList.remove('is-in'); }
        qsa('.sim-notif', notifStack).forEach(function (n) { n.remove(); });
        await delay(1000);
      }
    }

    runLoop();
  }

  /* =========================================================
     4. The Approval Transit — ForgeFlow Signature Interaction
     ========================================================= */
  var TRANSIT_STATIONS = [
    { id: 'emp',  label: 'Employee',     sub: 'Priya Sharma', dept: 'Engineering',   color: '#4f46e5', action: 'Request submitted',  ms: 600  },
    { id: 'it',   label: 'IT Head',      sub: 'Rohan Mehta',  dept: 'IT Department', color: '#f59e0b', action: 'Reviewing request…',  ms: 2200 },
    { id: 'hr',   label: 'HR Director',  sub: 'Meera Iyer',   dept: 'Human Resources', color: '#f59e0b', action: 'Reviewing request…', ms: 2200 },
    { id: 'fin',  label: 'Finance Head', sub: 'Karan Singh',  dept: 'Finance',       color: '#f59e0b', action: 'Final review…',       ms: 1800 },
    { id: 'done', label: 'Issued',       sub: 'Auto-generated', dept: 'ForgeFlow', color: '#10b981', action: 'QR slip generated',    ms: 600  }
  ];

  function initTransit() {
    var btn    = qs('#transit-btn');
    var track  = qs('#transit-track-fill');
    var token  = qs('#transit-token');
    var nodes  = qsa('.transit-node');
    var log    = qs('#transit-log');

    if (!btn || !track || !token || !nodes.length) return;

    var running = false;

    function resetTransit() {
      if (track)  track.style.width = '0%';
      if (token)  { token.style.left = '0%'; token.classList.remove('is-active'); }
      nodes.forEach(function (n) { n.classList.remove('is-active', 'is-done', 'is-approved', 'is-pending'); });
      if (log) log.innerHTML = '';
    }

    function logEntry(station, isApproval) {
      if (!log) return;
      var row = document.createElement('div');
      row.className = 'transit-log-row' + (isApproval ? ' is-approved' : '');
      var now = new Date();
      var time = now.getHours() + ':' + String(now.getMinutes()).padStart(2, '0');
      row.innerHTML =
        '<span class="transit-log-dot" style="background:' + station.color + '"></span>' +
        '<span class="transit-log-label">' + station.action + ' · <strong>' + station.label + '</strong></span>' +
        '<span class="transit-log-time">' + time + '</span>';
      log.appendChild(row);
      log.scrollTop = log.scrollHeight;
    }

    function setTokenPos(pct) {
      if (token) token.style.left = 'calc(' + pct + '% - 12px)';
    }

    btn.addEventListener('click', function () {
      if (running) return;
      running = true;
      btn.disabled = true;
      btn.textContent = 'Simulating…';
      btn.classList.add('is-running');
      resetTransit();

      var stationPcts = [];
      nodes.forEach(function (n, i) {
        stationPcts.push((i / (nodes.length - 1)) * 100);
      });

      var nodeArr = Array.from(nodes);

      (async function run() {
        // Activate token
        if (token) token.classList.add('is-active');

        for (var i = 0; i < TRANSIT_STATIONS.length; i++) {
          var station = TRANSIT_STATIONS[i];
          var pct = stationPcts[i];

          // Animate token to this node
          setTokenPos(pct);
          if (track) track.style.width = pct + '%';

          await delay(600);

          // Activate this node
          if (nodeArr[i]) {
            nodeArr[i].classList.add('is-active', 'is-pending');
          }

          logEntry(station, false);
          await delay(station.ms);

          // Mark approved/done
          if (nodeArr[i]) {
            nodeArr[i].classList.remove('is-pending');
            nodeArr[i].classList.add('is-approved');
          }

          // Mark previous as done
          if (i > 0 && nodeArr[i - 1]) {
            nodeArr[i - 1].classList.remove('is-active');
            nodeArr[i - 1].classList.add('is-done');
          }

          if (i === TRANSIT_STATIONS.length - 1) {
            logEntry({ action: 'Complete', label: 'Issued in 2h 16m', color: '#10b981' }, true);
          } else {
            logEntry({ action: station.id === 'emp' ? 'Submitted' : 'Approved ✓', label: station.label, color: '#10b981' }, true);
          }

          await delay(300);
        }

        await delay(1200);
        btn.disabled = false;
        btn.textContent = 'Replay journey';
        btn.classList.remove('is-running');
        running = false;
      })();
    });
  }

  /* =========================================================
     5. Cursor parallax (hero only)
     ========================================================= */
  function initParallax() {
    var hero = qs('.lp-hero-section');
    if (!hero) return;
    var layers = qsa('[data-depth]', hero);
    var raf = null;

    hero.addEventListener('mousemove', function (e) {
      if (raf) return;
      raf = requestAnimationFrame(function () {
        raf = null;
        var r  = hero.getBoundingClientRect();
        var dx = ((e.clientX - r.left) / r.width  - 0.5) * 2;
        var dy = ((e.clientY - r.top)  / r.height - 0.5) * 2;
        layers.forEach(function (l) {
          var d = parseFloat(l.getAttribute('data-depth')) || 1;
          l.style.transform = 'translate3d(' + dx * d * 12 + 'px,' + dy * d * 7 + 'px, 0)';
        });
      });
    });

    hero.addEventListener('mouseleave', function () {
      layers.forEach(function (l) { l.style.transform = ''; });
    });
  }

  /* =========================================================
     6. Card tilt
     ========================================================= */
  function initCardTilt() {
    qsa('.lp-feature, .lp-testimonial, .lp-plan').forEach(function (card) {
      card.style.transformStyle = 'preserve-3d';
      card.style.perspective = '800px';

      card.addEventListener('mousemove', function (e) {
        var r = card.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width  - 0.5;
        var y = (e.clientY - r.top)  / r.height - 0.5;
        card.style.transform = 'translateY(-3px) rotateX(' + (-y * 6) + 'deg) rotateY(' + (x * 6) + 'deg)';
        card.style.transition = 'transform 60ms linear';
      });

      card.addEventListener('mouseleave', function () {
        card.style.transform = '';
        card.style.transition = 'transform 400ms cubic-bezier(0.34,1.56,0.64,1), box-shadow 200ms, border-color 200ms';
      });
    });
  }

  /* =========================================================
     7. Theme transition smoothing
     ========================================================= */
  function initThemeSmooth() {
    qsa('[data-theme-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.documentElement.classList.add('theme-switching');
        setTimeout(function () { document.documentElement.classList.remove('theme-switching'); }, 600);
      });
    });
  }

  /* =========================================================
     8. Audit log reveal — stagger rows
     ========================================================= */
  function initAuditReveal() {
    if (!('IntersectionObserver' in window)) return;
    var visual = qs('.lp-audit-visual');
    if (!visual) return;

    var rows = qsa('.lp-audit-row', visual);
    rows.forEach(function (r) { r.style.opacity = '0'; r.style.transform = 'translateX(-12px)'; });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        rows.forEach(function (r, i) {
          setTimeout(function () {
            r.style.transition = 'opacity 380ms ease, transform 380ms cubic-bezier(0.19,1,0.22,1)';
            r.style.opacity    = '1';
            r.style.transform  = 'translateX(0)';
          }, i * 100);
        });
        io.unobserve(e.target);
      });
    }, { threshold: 0.3 });

    io.observe(visual);
  }

  /* =========================================================
     Boot
     ========================================================= */
  document.addEventListener('DOMContentLoaded', function () {
    initReveal();
    initCounters();
    initHeroSim();
    initTransit();
    initParallax();
    initCardTilt();
    initThemeSmooth();
    initAuditReveal();

    // Immediately reveal above-fold hero elements
    setTimeout(function () {
      qsa('.lp-hero-section [data-reveal]').forEach(function (el, i) {
        setTimeout(function () { el.classList.add('is-revealed'); }, 60 + i * 90);
      });
    }, 0);

    // Auto-start hero sim
    setTimeout(function () {
      var btn = qs('#transit-btn');
      if (btn && !btn.disabled) btn.click();
    }, 1200);
  });

})();
