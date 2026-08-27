/* ==========================================================================
   ForgeFlow Landing: Animation Engine v3
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
     1. Section reveal: IntersectionObserver
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
     Enterprise Workflow Scenarios (4-Tier Matrix)
     ========================================================= */
  var WORKFLOW_SCENARIOS = {
    equipment: {
      id: 'equipment',
      name: 'Equipment',
      type: 'Equipment Requisition',
      title: 'MacBook Pro 16" M3 Max',
      dept: 'Engineering · Bangalore',
      summary: 'MacBook Pro 16" · Equipment Requisition',
      code: 'ANK-3291',
      qrLabel: 'Asset Handover Voucher',
      qrSub: 'Signed · Serial #MBP-9482 · Scannable at IT Desk',
      stations: [
        { id: 'emp',  label: 'Employee',     role: 'Rajdeep Rathod',  dept: 'Engineering',        badgeIcon: 'bi-person-circle', color: '#4f46e5', action: 'Asset request submitted',      ms: 500 },
        { id: 'mgr',  label: 'Unit Manager', role: 'Vikram Sahay',   dept: 'Engineering Lead',   badgeIcon: 'bi-person-badge',  color: '#f59e0b', action: 'Budget & necessity verified',   ms: 1500 },
        { id: 'it',   label: 'IT Head',      role: 'Rohan Mehta',    dept: 'IT Infrastructure',  badgeIcon: 'bi-pc-display',    color: '#f59e0b', action: 'Asset #MBP-9482 assigned',     ms: 1500 },
        { id: 'done', label: 'Asset Issued', role: 'QR Voucher',     dept: 'Auto-Generated',     badgeIcon: 'bi-qr-code',       color: '#10b981', action: 'Digital handover slip issued',  ms: 600 }
      ],
      heroSteps: [
        { label: 'Submitted',        ms: 1500, run: function(ctx) { ctx.setProgress(12); ctx.activateDot(0); ctx.showCard(); } },
        { label: 'Manager Review',   ms: 1800, run: function(ctx) { ctx.setProgress(35); ctx.activateDot(1); ctx.showNotif('Vikram Sahay reviewing', 'warning'); } },
        { label: 'Manager Approved', ms: 1400, run: function(ctx) { ctx.setProgress(55); ctx.activateDot(2); ctx.updateBadge('1/2 Approved'); ctx.showNotif('Manager approved', 'success'); } },
        { label: 'IT Head Review',   ms: 1800, run: function(ctx) { ctx.setProgress(75); ctx.activateDot(3); ctx.showNotif('Rohan Mehta assigning asset', 'warning'); } },
        { label: 'IT Approved ✓',    ms: 1400, run: function(ctx) { ctx.setProgress(90); ctx.activateDot(4); ctx.updateBadge('2/2 Approved'); ctx.showNotif('IT Head approved', 'success'); } },
        { label: 'Voucher Issued',   ms: 2400, run: function(ctx) { ctx.setProgress(100); ctx.activateDot(5); ctx.showQR('Asset Handover Voucher', 'Signed · Serial #MBP-9482 · Ready for pickup'); ctx.showNotif('QR slip emailed to Rajdeep', 'success'); } }
      ]
    },
    expense: {
      id: 'expense',
      name: 'Expense',
      type: 'Expense Reimbursement',
      title: 'Client Onsite Travel ($1,420)',
      dept: 'Solutions & Sales · Mumbai',
      summary: 'Client Travel ($1,420) · Expense Reimbursement',
      code: 'ANK-4105',
      qrLabel: 'Payment Voucher Authorized',
      qrSub: 'Direct ACH payout scheduled · Reference #TXN-8821',
      stations: [
        { id: 'emp',  label: 'Employee',     role: 'Rajdeep Rathod',  dept: 'Solutions Team',     badgeIcon: 'bi-person-circle', color: '#4f46e5', action: 'Expense receipt submitted',     ms: 500 },
        { id: 'mgr',  label: 'Unit Manager', role: 'Vikram Sahay',   dept: 'Sales Director',     badgeIcon: 'bi-person-badge',  color: '#f59e0b', action: 'Travel policy compliance ok',   ms: 1500 },
        { id: 'fin',  label: 'Finance Lead', role: 'Karan Singh',    dept: 'Finance & Accounts', badgeIcon: 'bi-bank',          color: '#f59e0b', action: 'Payment voucher authorized',     ms: 1500 },
        { id: 'done', label: 'Disbursed',    role: 'Direct ACH',     dept: 'Auto-Transfer',      badgeIcon: 'bi-patch-check-fill', color: '#10b981', action: 'ACH disbursement batch created', ms: 600 }
      ],
      heroSteps: [
        { label: 'Submitted',        ms: 1500, run: function(ctx) { ctx.setProgress(12); ctx.activateDot(0); ctx.showCard(); } },
        { label: 'Manager Review',   ms: 1800, run: function(ctx) { ctx.setProgress(35); ctx.activateDot(1); ctx.showNotif('Vikram Sahay checking receipts', 'warning'); } },
        { label: 'Manager Approved', ms: 1400, run: function(ctx) { ctx.setProgress(55); ctx.activateDot(2); ctx.updateBadge('1/2 Approved'); ctx.showNotif('Manager approved', 'success'); } },
        { label: 'Finance Review',   ms: 1800, run: function(ctx) { ctx.setProgress(75); ctx.activateDot(3); ctx.showNotif('Karan Singh authorizing payout', 'warning'); } },
        { label: 'Finance Approved', ms: 1400, run: function(ctx) { ctx.setProgress(90); ctx.activateDot(4); ctx.updateBadge('2/2 Approved'); ctx.showNotif('Finance authorized', 'success'); } },
        { label: 'Disbursed',        ms: 2400, run: function(ctx) { ctx.setProgress(100); ctx.activateDot(5); ctx.showQR('Payment Voucher Authorized', 'Direct ACH transfer scheduled · Ref #TXN-8821'); ctx.showNotif('ACH transfer queued for Rajdeep', 'success'); } }
      ]
    },
    access: {
      id: 'access',
      name: 'Access',
      type: 'Security Clearance',
      title: 'Production Database & VPN',
      dept: 'DevOps & Cloud · Bangalore',
      summary: 'Production Database · Security Clearance',
      code: 'ANK-5082',
      qrLabel: 'Temporary IAM Session Granted',
      qrSub: 'Single-session cryptographic token · Expires in 24h',
      stations: [
        { id: 'emp',  label: 'Employee',     role: 'Rajdeep Rathod',  dept: 'DevOps Engineer',    badgeIcon: 'bi-person-circle', color: '#4f46e5', action: 'Elevated access requested',    ms: 500 },
        { id: 'lead', label: 'Tech Lead',    role: 'Vikram Sahay',   dept: 'Principal Architect',badgeIcon: 'bi-person-badge',  color: '#f59e0b', action: 'Change ticket #CR-904 validated',ms: 1500 },
        { id: 'sec',  label: 'IT Security',  role: 'Neha Kapoor',    dept: 'InfoSec Lead',       badgeIcon: 'bi-shield-check',  color: '#f59e0b', action: 'MFA clearance & role bound',    ms: 1500 },
        { id: 'done', label: 'Access Granted', role: '24h IAM Token', dept: 'Auto-Bound',        badgeIcon: 'bi-key-fill',      color: '#10b981', action: 'Session token provisioned',     ms: 600 }
      ],
      heroSteps: [
        { label: 'Submitted',        ms: 1500, run: function(ctx) { ctx.setProgress(12); ctx.activateDot(0); ctx.showCard(); } },
        { label: 'Architect Review', ms: 1800, run: function(ctx) { ctx.setProgress(35); ctx.activateDot(1); ctx.showNotif('Vikram Sahay verifying ticket', 'warning'); } },
        { label: 'Architect Approved', ms: 1400, run: function(ctx) { ctx.setProgress(55); ctx.activateDot(2); ctx.updateBadge('1/2 Approved'); ctx.showNotif('Architect approved', 'success'); } },
        { label: 'Security Review',  ms: 1800, run: function(ctx) { ctx.setProgress(75); ctx.activateDot(3); ctx.showNotif('Neha Kapoor checking policy', 'warning'); } },
        { label: 'Security Approved', ms: 1400, run: function(ctx) { ctx.setProgress(90); ctx.activateDot(4); ctx.updateBadge('2/2 Approved'); ctx.showNotif('Security approved', 'success'); } },
        { label: 'Access Granted',   ms: 2400, run: function(ctx) { ctx.setProgress(100); ctx.activateDot(5); ctx.showQR('24h IAM Token Active', 'Cryptographic session generated · Single-use'); ctx.showNotif('Access token provisioned for Rajdeep', 'success'); } }
      ]
    },
    leave: {
      id: 'leave',
      name: 'Leave',
      type: 'Time Off Request',
      title: 'Annual Vacation (4 Days)',
      dept: 'Engineering · Bangalore',
      summary: 'Annual Vacation (4 Days) · Time Off Request',
      code: 'ANK-6194',
      qrLabel: 'Leave Approved & Synced',
      qrSub: 'Google Calendar synchronized · 16 days balance remaining',
      stations: [
        { id: 'emp',  label: 'Employee',     role: 'Rajdeep Rathod',  dept: 'Engineering',        badgeIcon: 'bi-person-circle', color: '#4f46e5', action: 'Leave request submitted',      ms: 500 },
        { id: 'mgr',  label: 'Unit Manager', role: 'Vikram Sahay',   dept: 'Engineering Lead',   badgeIcon: 'bi-person-badge',  color: '#f59e0b', action: 'Sprint coverage confirmed',     ms: 1500 },
        { id: 'hr',   label: 'HR Operations', role: 'Meera Iyer',     dept: 'Human Resources',    badgeIcon: 'bi-people',        color: '#f59e0b', action: 'Balance deducted (16 left)',    ms: 1500 },
        { id: 'done', label: 'Approved',     role: 'Calendar Synced',dept: 'Auto-Update',        badgeIcon: 'bi-calendar2-check-fill', color: '#10b981', action: 'Calendar & HR records updated', ms: 600 }
      ],
      heroSteps: [
        { label: 'Submitted',        ms: 1500, run: function(ctx) { ctx.setProgress(12); ctx.activateDot(0); ctx.showCard(); } },
        { label: 'Manager Review',   ms: 1800, run: function(ctx) { ctx.setProgress(35); ctx.activateDot(1); ctx.showNotif('Vikram Sahay checking coverage', 'warning'); } },
        { label: 'Manager Approved', ms: 1400, run: function(ctx) { ctx.setProgress(55); ctx.activateDot(2); ctx.updateBadge('1/2 Approved'); ctx.showNotif('Manager approved', 'success'); } },
        { label: 'HR Review',        ms: 1800, run: function(ctx) { ctx.setProgress(75); ctx.activateDot(3); ctx.showNotif('Meera Iyer validating balance', 'warning'); } },
        { label: 'HR Approved ✓',    ms: 1400, run: function(ctx) { ctx.setProgress(90); ctx.activateDot(4); ctx.updateBadge('2/2 Approved'); ctx.showNotif('HR approved', 'success'); } },
        { label: 'Leave Confirmed',  ms: 2400, run: function(ctx) { ctx.setProgress(100); ctx.activateDot(5); ctx.showQR('Leave Approved & Synced', 'Calendar updated · 16 days balance left'); ctx.showNotif('Leave confirmation sent to Rajdeep', 'success'); } }
      ]
    }
  };

  var SCENARIO_KEYS = ['equipment', 'expense', 'access', 'leave'];

  /* =========================================================
     3. Hero simulation: Multi-workflow state machine
     ========================================================= */
  function initHeroSim() {
    var sim = qs('#hero-sim');
    if (!sim) return;

    var progressBar   = qs('#sim-progress');
    var stateLabel    = qs('#sim-state-label');
    var stepDots      = qsa('.sim-dot', sim);
    var requestCard   = qs('#sim-request-card');
    var notifStack    = qs('#sim-notif-stack');
    var qrReveal      = qs('#sim-qr');

    var typeEl        = qs('.sim-card__request-type', sim);
    var titleEl       = qs('.sim-card__request-title', sim);
    var deptEl        = qs('.sim-card__dept', sim);
    var badgeEl       = qs('.sim-card__badge', sim);
    var qrLabelEl     = qs('.sim-qr__label', sim);
    var qrSubEl       = qs('.sim-qr__sub', sim);

    var scenarioIndex = 0;
    var running       = true;

    var ctx = {
      setProgress: function (pct) {
        if (progressBar) progressBar.style.width = pct + '%';
      },
      activateDot: function (idx) {
        stepDots.forEach(function (d, i) {
          d.classList.toggle('is-active', i === idx);
          d.classList.toggle('is-done', i < idx);
        });
      },
      showCard: function () {
        if (requestCard) {
          requestCard.classList.remove('is-hidden');
          requestCard.classList.add('is-in');
        }
      },
      updateBadge: function (text) {
        if (badgeEl) badgeEl.textContent = text;
      },
      showQR: function (label, sub) {
        if (qrLabelEl) qrLabelEl.textContent = label;
        if (qrSubEl) qrSubEl.textContent = sub;
        if (qrReveal) qrReveal.classList.add('is-in');
      },
      showNotif: function (text, type) {
        if (!notifStack) return;
        var n = document.createElement('div');
        n.className = 'sim-notif sim-notif--' + type;
        n.innerHTML = '<i class="bi bi-bell-fill"></i><span>' + text + '</span>';
        notifStack.prepend(n);
        requestAnimationFrame(function () { n.classList.add('is-in'); });
        setTimeout(function () {
          n.classList.remove('is-in');
          setTimeout(function () { if (n.parentNode) n.parentNode.removeChild(n); }, 350);
        }, 2800);
      }
    };

    async function runLoop() {
      while (running) {
        var key = SCENARIO_KEYS[scenarioIndex % SCENARIO_KEYS.length];
        var scn = WORKFLOW_SCENARIOS[key];
        scenarioIndex++;

        // Bind scenario card data
        if (typeEl)   typeEl.textContent   = scn.type;
        if (titleEl)  titleEl.textContent  = scn.title;
        if (deptEl)   deptEl.textContent   = scn.dept;
        if (badgeEl)  badgeEl.textContent  = '0/2 Approved';

        for (var i = 0; i < scn.heroSteps.length; i++) {
          var step = scn.heroSteps[i];
          if (stateLabel) stateLabel.textContent = step.label;
          step.run(ctx);
          await delay(step.ms);
        }

        // Reset for next scenario
        ctx.setProgress(0);
        ctx.activateDot(-1);
        if (requestCard) requestCard.classList.remove('is-in');
        if (qrReveal)    qrReveal.classList.remove('is-in');
        qsa('.sim-notif', notifStack).forEach(function (n) { n.remove(); });
        await delay(900);
      }
    }

    runLoop();
  }

  /* =========================================================
     4. The Approval Transit: Interactive Multi-Workflow Engine
     ========================================================= */
  function initTransit() {
    var btn        = qs('#transit-btn');
    var track      = qs('#transit-track-fill');
    var token      = qs('#transit-token');
    var nodesWrap  = qs('#transit-nodes');
    var log        = qs('#transit-log');
    var pillsWrap  = qs('#transit-scenario-pills');
    var summaryEl  = qs('#transit-req-summary');
    var titleEl    = qs('.lp-transit-log-panel__title');

    if (!btn || !track || !token || !nodesWrap) return;

    var currentScenarioKey = 'equipment';
    var isSimulating       = false;

    function renderStations(scenario) {
      if (!nodesWrap) return;
      nodesWrap.innerHTML = scenario.stations.map(function (st) {
        return (
          '<div class="transit-node" data-station="' + st.id + '">' +
            '<div class="transit-node__badge"><i class="bi ' + st.badgeIcon + '"></i></div>' +
            '<div class="transit-node__name">' + st.label + '</div>' +
            '<div class="transit-node__role">' + st.role + '</div>' +
          '</div>'
        );
      }).join('');

      if (summaryEl) summaryEl.textContent = scenario.summary;
      if (titleEl)   titleEl.innerHTML = '<i class="bi bi-clock-history" style="margin-right: 6px;"></i> Audit log · ' + scenario.code;
    }

    function resetTransitVisuals() {
      if (track) track.style.width = '0%';
      if (token) { token.style.left = '0%'; token.classList.remove('is-active'); }
      var nodes = qsa('.transit-node', nodesWrap);
      nodes.forEach(function (n) { n.classList.remove('is-active', 'is-done', 'is-approved', 'is-pending'); });
    }

    function logEntry(station, isComplete) {
      if (!log) return;
      var row = document.createElement('div');
      row.className = 'transit-log-row' + (isComplete ? ' is-approved' : '');
      var now = new Date();
      var time = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
      row.innerHTML =
        '<span class="transit-log-dot" style="background:' + station.color + '"></span>' +
        '<span class="transit-log-label">' + station.action + ' · <strong>' + station.label + '</strong></span>' +
        '<span class="transit-log-time">' + time + '</span>';
      log.appendChild(row);
      log.scrollTop = log.scrollHeight;
    }

    function selectScenario(key) {
      if (isSimulating) return;
      currentScenarioKey = key;

      // Update active pill
      if (pillsWrap) {
        qsa('.lp-scenario-pill', pillsWrap).forEach(function (p) {
          p.classList.toggle('is-active', p.getAttribute('data-scenario') === key);
        });
      }

      var scn = WORKFLOW_SCENARIOS[key];
      renderStations(scn);
      resetTransitVisuals();

      if (log) {
        log.innerHTML =
          '<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 160px; color: var(--text-tertiary); font-size: var(--text-xs); text-align: center; padding: var(--sp-6);">' +
            '<i class="bi bi-arrow-left-circle" style="font-size: 24px; margin-bottom: var(--sp-3); opacity: 0.4;"></i>' +
            'Selected: <strong>' + scn.type + '</strong><br>Press "Submit a request" to simulate live approval.' +
          '</div>';
      }
    }

    // Pill click listeners
    if (pillsWrap) {
      pillsWrap.addEventListener('click', function (e) {
        var pill = e.target.closest('.lp-scenario-pill');
        if (!pill || isSimulating) return;
        var scnKey = pill.getAttribute('data-scenario');
        if (scnKey && WORKFLOW_SCENARIOS[scnKey]) {
          selectScenario(scnKey);
        }
      });
    }

    // Initialize first scenario
    renderStations(WORKFLOW_SCENARIOS.equipment);

    // Simulation trigger
    btn.addEventListener('click', function () {
      if (isSimulating) return;
      isSimulating = true;
      btn.disabled = true;
      btn.textContent = 'Simulating…';
      btn.classList.add('is-running');

      var scn = WORKFLOW_SCENARIOS[currentScenarioKey];
      var nodes = qsa('.transit-node', nodesWrap);
      if (log) log.innerHTML = '';
      resetTransitVisuals();

      var stationPcts = [];
      nodes.forEach(function (n, i) {
        stationPcts.push((i / (nodes.length - 1)) * 100);
      });

      var nodeArr = Array.from(nodes);

      (async function run() {
        if (token) token.classList.add('is-active');

        for (var i = 0; i < scn.stations.length; i++) {
          var station = scn.stations[i];
          var pct = stationPcts[i];

          // Move token & fill track
          if (token) token.style.left = 'calc(' + pct + '% - 12px)';
          if (track) track.style.width = pct + '%';

          await delay(500);

          // Activate node
          if (nodeArr[i]) nodeArr[i].classList.add('is-active', 'is-pending');
          logEntry(station, false);

          await delay(station.ms);

          // Node approved
          if (nodeArr[i]) {
            nodeArr[i].classList.remove('is-pending');
            nodeArr[i].classList.add('is-approved');
          }

          // Previous marked done
          if (i > 0 && nodeArr[i - 1]) {
            nodeArr[i - 1].classList.remove('is-active');
            nodeArr[i - 1].classList.add('is-done');
          }

          if (i === scn.stations.length - 1) {
            logEntry({ action: 'Complete', label: scn.qrLabel, color: '#10b981' }, true);
          } else {
            logEntry({ action: station.id === 'emp' ? 'Submitted' : 'Approved ✓', label: station.label, color: '#10b981' }, true);
          }

          await delay(250);
        }

        await delay(900);
        btn.disabled = false;
        btn.textContent = 'Replay journey';
        btn.classList.remove('is-running');
        isSimulating = false;
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
     8. Audit log reveal: stagger rows
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
  });

})();
