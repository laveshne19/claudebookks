/* ============================================================
   NALANDA X — Interaction + Animation Engine
   No dependencies. 60fps (transform/opacity only). a11y-aware.
   ============================================================ */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- Scroll reveal via IntersectionObserver ---- */
  function initReveal() {
    if (reduce || !('IntersectionObserver' in window)) {
      document.querySelectorAll('[data-reveal],[data-reveal-stagger]').forEach(function (el) { el.classList.add('in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target;
        if (el.hasAttribute('data-reveal-stagger')) {
          Array.prototype.forEach.call(el.children, function (child, i) {
            child.style.transitionDelay = (i * 70) + 'ms';
          });
        }
        el.classList.add('in');
        io.unobserve(el);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.12 });
    document.querySelectorAll('[data-reveal],[data-reveal-stagger]').forEach(function (el) { io.observe(el); });
  }

  /* ---- Sticky header shadow ---- */
  function initHeader() {
    var h = document.querySelector('[data-header]');
    if (!h) return;
    var onScroll = function () { h.classList.toggle('is-stuck', window.scrollY > 8); };
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
  }

  /* ---- Hero parallax (rAF-throttled) ---- */
  function initParallax() {
    if (reduce) return;
    var nodes = document.querySelectorAll('[data-parallax]');
    if (!nodes.length) return;
    var ticking = false;
    function update() {
      var y = window.scrollY;
      nodes.forEach(function (n) {
        var speed = parseFloat(n.getAttribute('data-parallax')) || 0.2;
        n.style.transform = 'translate3d(0,' + (y * speed) + 'px,0)';
      });
      ticking = false;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { window.requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
  }

  /* ---- Magnetic buttons ---- */
  function initMagnetic() {
    if (reduce || window.matchMedia('(pointer: coarse)').matches) return;
    document.querySelectorAll('[data-magnetic]').forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect();
        var x = e.clientX - r.left - r.width / 2;
        var y = e.clientY - r.top - r.height / 2;
        el.style.transform = 'translate(' + x * 0.25 + 'px,' + y * 0.35 + 'px)';
      });
      el.addEventListener('mouseleave', function () { el.style.transform = ''; });
    });
  }

  /* ---- PDP gallery ---- */
  function initGallery() {
    document.querySelectorAll('[data-gallery]').forEach(function (g) {
      var main = g.querySelector('[data-gallery-main]');
      g.querySelectorAll('[data-gallery-thumb]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (main) { main.src = btn.getAttribute('data-full'); main.alt = btn.querySelector('img') ? btn.querySelector('img').alt : ''; }
          g.querySelectorAll('[data-gallery-thumb]').forEach(function (b) { b.setAttribute('aria-current', 'false'); });
          btn.setAttribute('aria-current', 'true');
        });
      });
    });
  }

  /* ---- Variant selection (single-option, simple) ---- */
  function initVariants() {
    document.querySelectorAll('[data-variants]').forEach(function (root) {
      root.querySelectorAll('[data-variant]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          root.querySelectorAll('[data-variant]').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
          btn.setAttribute('aria-pressed', 'true');
          var idInput = document.querySelector('[data-variant-id]');
          if (idInput) idInput.value = btn.getAttribute('data-variant');
          var priceEl = document.querySelector('[data-current-price]');
          if (priceEl && btn.getAttribute('data-price')) priceEl.textContent = btn.getAttribute('data-price');
        });
      });
    });
  }

  /* ---- Sticky mobile buy bar ---- */
  function initStickyBuy() {
    var bar = document.querySelector('[data-sticky-buy]');
    var anchor = document.querySelector('[data-buy-anchor]');
    if (!bar || !anchor || !('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function (e) {
      bar.classList.toggle('is-visible', !e[0].isIntersecting);
    }, { threshold: 0 });
    io.observe(anchor);
  }

  /* ---- Cart drawer + AJAX add ---- */
  function openDrawer() { var d = document.querySelector('[data-cart-drawer]'); if (d) { d.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden'; } }
  function closeDrawer() { var d = document.querySelector('[data-cart-drawer]'); if (d) { d.setAttribute('aria-hidden', 'true'); document.body.style.overflow = ''; } }

  function refreshCart() {
    return fetch('/cart.js', { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        document.querySelectorAll('[data-cart-count]').forEach(function (n) { n.textContent = cart.item_count; n.hidden = cart.item_count === 0; });
        return cart;
      });
  }

  function initCart() {
    document.addEventListener('click', function (e) {
      var open = e.target.closest('[data-open-cart]');
      var close = e.target.closest('[data-close-cart]');
      if (open) { e.preventDefault(); openDrawer(); }
      if (close) { e.preventDefault(); closeDrawer(); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDrawer(); });

    document.querySelectorAll('form[action$="/cart/add"]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        if (form.hasAttribute('data-no-ajax')) return;
        e.preventDefault();
        var btn = form.querySelector('[type="submit"]');
        if (btn) { btn.disabled = true; btn.dataset.label = btn.textContent; btn.textContent = 'Adding…'; }
        fetch('/cart/add.js', { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } })
          .then(function (r) { return r.json(); })
          .then(function () { return refreshCart(); })
          .then(function () { openDrawer(); })
          .catch(function () { form.submit(); })
          .finally(function () { if (btn) { btn.disabled = false; btn.textContent = btn.dataset.label || 'Add to Cart'; } });
      });
    });
    refreshCart();
  }

  /* ---- Predictive search (Shopify Search & Discovery API) ---- */
  function initSearch() {
    var input = document.querySelector('[data-search-input]');
    var panel = document.querySelector('[data-search-results]');
    if (!input || !panel) return;
    var t;
    input.addEventListener('input', function () {
      clearTimeout(t);
      var q = input.value.trim();
      if (q.length < 2) { panel.innerHTML = ''; panel.hidden = true; return; }
      t = setTimeout(function () {
        fetch('/search/suggest.json?q=' + encodeURIComponent(q) + '&resources[type]=product&resources[limit]=6')
          .then(function (r) { return r.json(); })
          .then(function (data) {
            var items = (data.resources && data.resources.results && data.resources.results.products) || [];
            panel.innerHTML = items.map(function (p) {
              return '<a class="search__item" href="' + p.url + '">' +
                (p.featured_image ? '<img src="' + p.featured_image.url + '" alt="" width="40" height="40">' : '') +
                '<span>' + p.title + '</span></a>';
            }).join('') || '<div class="search__empty">No matches</div>';
            panel.hidden = false;
          });
      }, 220);
    });
  }

  function ready(fn) { if (document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  ready(function () {
    initReveal(); initHeader(); initParallax(); initMagnetic();
    initGallery(); initVariants(); initStickyBuy(); initCart(); initSearch();
  });
})();
