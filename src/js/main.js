(function () {
  var doc = document.documentElement;

  // цели Метрики: звонок, мессенджер, заявка
  function goal(name) {
    (window.YM_IDS || []).forEach(function (id) {
      if (window.ym) window.ym(id, 'reachGoal', name);
    });
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-goal]');
    if (a) goal(a.getAttribute('data-goal'));
  });

  // мобильное меню
  var burger = document.querySelector('.burger');
  if (burger) {
    burger.addEventListener('click', function () {
      var open = doc.classList.toggle('menu-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  // выпадающие списки: закрывать по клику вне и при открытии соседнего
  var subs = document.querySelectorAll('.has-sub details');
  subs.forEach(function (d) {
    d.addEventListener('toggle', function () {
      if (d.open) subs.forEach(function (o) { if (o !== d) o.open = false; });
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.has-sub') && window.innerWidth > 1080) subs.forEach(function (d) { d.open = false; });
  });

  // cookie
  var cookie = document.getElementById('cookie');
  try {
    if (cookie && !localStorage.getItem('cookie-ok')) cookie.hidden = false;
  } catch (err) { if (cookie) cookie.hidden = false; }
  var ok = document.getElementById('cookie-ok');
  if (ok) ok.addEventListener('click', function () {
    cookie.hidden = true;
    try { localStorage.setItem('cookie-ok', '1'); } catch (err) {}
  });

  // форма «Перезвоните мне»
  document.querySelectorAll('.lead-form').forEach(function (form) {
    var msg = form.querySelector('.form-msg');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var phone = form.elements.phone;
      var digits = phone.value.replace(/\D/g, '');
      msg.className = 'form-msg is-err';
      if (digits.length < 10) {
        phone.setAttribute('aria-invalid', 'true');
        msg.textContent = 'Проверьте номер телефона.';
        phone.focus();
        return;
      }
      phone.removeAttribute('aria-invalid');
      if (!form.elements.consent.checked) {
        msg.textContent = 'Нужно согласие на обработку персональных данных.';
        return;
      }
      if (form.elements.website.value) return;
      var endpoint = form.getAttribute('data-endpoint');
      if (!endpoint) {
        msg.textContent = 'Это демо-версия сайта: заявки пока не принимаются. Позвоните нам — 8 (927) 067-70-70.';
        return;
      }
      var btn = form.querySelector('button');
      btn.disabled = true;
      fetch(endpoint, { method: 'POST', body: new FormData(form) })
        .then(function (r) { if (!r.ok) throw new Error(r.status); })
        .then(function () {
          goal('lead');
          msg.className = 'form-msg';
          msg.textContent = 'Спасибо! Перезвоним в ближайшие минуты.';
          form.reset();
        })
        .catch(function () {
          msg.textContent = 'Не удалось отправить. Позвоните нам — 8 (927) 067-70-70.';
        })
        .then(function () { btn.disabled = false; });
    });
  });

  // плавное появление блоков
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if ('IntersectionObserver' in window) {
    var els = document.querySelectorAll('main .section h2, .svc-grid li, .sit-grid li, .why-card, .steps li, .geo-grid li, .gallery figure, .fleet-card, .stats li, .price-table tbody tr, .faq-item');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -40px 0px' });
    els.forEach(function (el) {
      // каскад: соседние элементы одной сетки появляются друг за другом
      var i = Array.prototype.indexOf.call(el.parentNode.children, el);
      if (i > 0) el.style.transitionDelay = Math.min(i, 8) * 60 + 'ms';
      el.classList.add('reveal');
      io.observe(el);
    });

    // счётчики: в HTML уже настоящее число (для поисковиков), анимируем только видимые
    var counters = document.querySelectorAll('[data-count]');
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        cio.unobserve(en.target);
        if (calm) return;
        var el = en.target, to = +el.getAttribute('data-count'), t0 = null;
        function step(t) {
          if (!t0) t0 = t;
          var p = Math.min((t - t0) / 1100, 1), v = Math.round(to * (1 - Math.pow(1 - p, 3)));
          el.textContent = v.toLocaleString('ru-RU');
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    counters.forEach(function (el) { cio.observe(el); });
  }

  // тень у шапки при прокрутке и лёгкий параллакс фото на первом экране
  var heroImg = document.querySelector('.hero-bg-img img');
  var ticking = false;
  function onScroll() {
    var y = window.scrollY;
    doc.classList.toggle('scrolled', y > 8);
    if (heroImg && !calm && window.innerWidth > 860 && y < window.innerHeight) {
      heroImg.style.transform = 'translate3d(0,' + (y * 0.22).toFixed(1) + 'px,0)';
    }
    ticking = false;
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  // карта территорий: Leaflet + OpenStreetMap, грузим только когда блок у экрана
  var mapEl = document.querySelector('.geo-map[data-points]');
  if (mapEl && 'IntersectionObserver' in window) {
    var LF = (document.querySelector('script[src*="/js/main.js"]').getAttribute('src').split('/js/main.js')[0]) + '/vendor/leaflet/';
    var mio = new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) return;
      mio.disconnect();
      var css = document.createElement('link');
      css.rel = 'stylesheet'; css.href = LF + 'leaflet.min.css';
      document.head.appendChild(css);
      var js = document.createElement('script');
      js.src = LF + 'leaflet.min.js';
      js.onload = function () {
        var L = window.L, pts = JSON.parse(mapEl.getAttribute('data-points'));
        mapEl.innerHTML = '';
        var map = L.map(mapEl, { scrollWheelZoom: false, zoomControl: true });
        map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 14, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(map);
        var bounds = [];
        pts.forEach(function (p, i) {
          var icon = L.divIcon({
            className: 'map-pin lbl-' + (p[4] || 'r') + (i === 0 ? ' is-main' : ''),
            html: '<span>' + p[0] + '</span>', iconSize: [18, 18], iconAnchor: [9, 9]
          });
          L.marker([p[1], p[2]], { icon: icon, title: p[0], keyboard: true })
            .on('click', function () { location.href = p[3]; }).addTo(map);
          bounds.push([p[1], p[2]]);
        });
        map.fitBounds(bounds, { padding: [40, 40] });
      };
      js.onerror = function () { mapEl.querySelector('.geo-map-ph').textContent = 'Карту не удалось загрузить.'; };
      document.head.appendChild(js);
    }, { rootMargin: '200px 0px' });
    mio.observe(mapEl);
  }
})();
