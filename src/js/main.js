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
  if ('IntersectionObserver' in window) {
    var els = document.querySelectorAll('main .section h2, .svc-grid li, .why-card, .steps li, .geo-grid li, .gallery figure, .fleet-card');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -40px 0px' });
    els.forEach(function (el) { el.classList.add('reveal'); io.observe(el); });
  }
})();
