"""Сборщик статического сайта эвакуатор-34.рф.

    python build.py          — черновая сборка в dist/ (пробелы в фактах видны пометками)
    python build.py --prod   — продакшен; откажется собирать, пока есть todo/draft
    python build.py --staging --base /evakuator-34
                             — превью для GitHub Pages: noindex, без Метрики, пути с префиксом
"""
import hashlib
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from PIL import Image

import content as C

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
PROD = "--prod" in sys.argv
STAGING = "--staging" in sys.argv
BASE = sys.argv[sys.argv.index("--base") + 1].rstrip("/") if "--base" in sys.argv else ""

S = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
URL = S["site_url"].rstrip("/")
TODAY = date.today().isoformat()
TODOS, DRAFTS = [], []


# ---------- факты ----------

def is_todo(key):
    v = S.get(key)
    return isinstance(v, dict) and "todo" in v


def fact(key):
    """Значение факта или видимая пометка «нужно от клиента»."""
    v = S.get(key)
    if isinstance(v, dict) and "todo" in v:
        TODOS.append(v["todo"])
        return f'<span class="todo">{esc(v["todo"])} — нужно от клиента</span>'
    if isinstance(v, dict):
        if v.get("draft"):
            DRAFTS.append(f'{key}: {v.get("note", v["value"])}')
        return esc(v["value"])
    return esc(v)


def esc(s):
    return html.escape(str(s), quote=True)


def price(name):
    for g in S["prices"]:
        for it in g["items"]:
            if it["name"] == name:
                return it
    raise KeyError(name)


TEL = S["phone"]
PHONE = esc(S["phone_display"])
SERVICES = {s["slug"]: s for s in C.SERVICES}
GEO = {g["slug"]: g for g in C.GEO}


# ---------- картинки ----------

def img_variants(name):
    files = sorted(SRC.glob(f"img/{name}-*.webp"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    out = []
    for p in files:
        with Image.open(p) as im:
            out.append((p.name, im.width, im.height))
    return out


def picture(name, alt, sizes="(max-width: 860px) 100vw, 50vw", eager=False, cls=""):
    v = img_variants(name)
    srcset = ", ".join(f"/img/{f} {w}w" for f, w, _ in v)
    f, w, h = v[-1]
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<img class="{cls}" src="/img/{f}" srcset="{srcset}" sizes="{sizes}" '
            f'width="{w}" height="{h}" alt="{esc(alt)}" {load}>')


# ---------- общие куски ----------

def tel_link(cls="btn btn-call", label=None, goal="call"):
    label = label or f'<span class="btn-ico" aria-hidden="true">{ICON_PHONE}</span><span>{PHONE}</span>'
    return f'<a class="{cls}" href="tel:{TEL}" data-goal="{goal}">{label}</a>'


def messenger_btn(key, label, href_tpl, cls="btn btn-ghost"):
    if is_todo(key):
        return f'<span class="{cls} is-todo">{label}: {fact(key)}</span>'
    return f'<a class="{cls}" href="{esc(href_tpl.format(S[key]))}" target="_blank" rel="noopener" data-goal="messenger">{label}</a>'


def mobile_msg():
    if is_todo("whatsapp"):
        fact("whatsapp")
        return '<span class="mb-msg is-todo"><span class="todo">WhatsApp — нужно от клиента</span></span>'
    return messenger_btn("whatsapp", "WhatsApp", "https://wa.me/{}", cls="mb-msg")


ICON_PHONE ='<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z"/></svg>'
ICON_CHECK = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>'
ICON_PIN = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>'

LOGO = ('<a class="logo" href="/" aria-label="Эвакуатор-34 — на главную">'
        '<span class="logo-mark" aria-hidden="true">34</span>'
        '<span class="logo-text"><b>Эвакуатор-34</b><small>Волжский и область · 24/7</small></span></a>')


def header():
    svc = "".join(f'<li><a href="/{s["slug"]}/">{esc(s["nav"])}</a></li>' for s in C.SERVICES)
    geo = '<li><a href="/">Волжский</a></li>' + "".join(
        f'<li><a href="/{g["slug"]}/">{esc(g["nav"])}</a></li>' for g in C.GEO)
    return f'''<header class="site-header">
  <div class="wrap header-in">
    {LOGO}
    <nav class="nav" id="nav" aria-label="Основное меню">
      <ul class="nav-list">
        <li class="has-sub"><details><summary>Услуги</summary><ul class="sub">{svc}</ul></details></li>
        <li class="has-sub"><details><summary>Где работаем</summary><ul class="sub">{geo}</ul></details></li>
        <li><a href="/tseny/">Цены</a></li>
        <li><a href="/kontakty/">Контакты</a></li>
      </ul>
    </nav>
    <div class="header-call">
      <a class="header-phone" href="tel:{TEL}" data-goal="call">{PHONE}</a>
      <span class="header-hours">круглосуточно</span>
    </div>
    <button class="burger" type="button" aria-controls="nav" aria-expanded="false" aria-label="Меню"><span></span></button>
  </div>
</header>'''


def footer():
    svc = "".join(f'<li><a href="/{s["slug"]}/">{esc(s["nav"])}</a></li>' for s in C.SERVICES)
    geo = '<li><a href="/">Волжский</a></li>' + "".join(
        f'<li><a href="/{g["slug"]}/">{esc(g["nav"])}</a></li>' for g in C.GEO)
    campaign = "%D1%8D%D0%B2%D0%B0%D0%BA%D1%83%D0%B0%D1%82%D0%BE%D1%80-34.%D1%80%D1%84"
    return f'''<footer class="site-footer">
  <div class="wrap footer-grid">
    <div>
      {LOGO}
      <p class="footer-phone"><a href="tel:{TEL}" data-goal="call">{PHONE}</a></p>
      <p>{esc(S["hours"])}</p>
      <p class="muted small">{fact("legal_name")}<br>ИНН {fact("inn")}</p>
    </div>
    <div><p class="footer-h">Услуги</p><ul>{svc}<li><a href="/tseny/">Все цены</a></li></ul></div>
    <div><p class="footer-h">Где работаем</p><ul>{geo}</ul></div>
    <div><p class="footer-h">Информация</p><ul>
      <li><a href="/kontakty/">Контакты</a></li>
      <li><a href="/politika-konfidencialnosti/">Политика конфиденциальности</a></li>
    </ul></div>
  </div>
  <div class="wrap footer-bottom">
    <span>© {date.today().year} {esc(S["brand"])} · {esc(S["domain_display"])}</span>
    <a class="studio" href="https://sitomika.ru/?utm_source=client_site&amp;utm_medium=footer&amp;utm_campaign={campaign}" target="_blank" rel="noopener">Разработано в sitomika.ru</a>
  </div>
</footer>
<div class="mobile-bar">
  <a class="mb-call" href="tel:{TEL}" data-goal="call">{ICON_PHONE}<span>Позвонить</span></a>
  {mobile_msg()}
</div>
<div class="cookie" id="cookie" hidden>
  <p>Мы используем cookie и Яндекс Метрику, чтобы сайт работал и становился удобнее. <a href="/politika-konfidencialnosti/">Подробнее</a></p>
  <button type="button" class="btn btn-small" id="cookie-ok">Понятно</button>
</div>'''


def metrika():
    if STAGING:  # превью не должно портить статистику боевого сайта
        return ""
    ids = S["metrika_ids"]
    inits = "".join(f'ym({i},"init",{{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true}});' for i in ids)
    noscript = "".join(f'<img src="https://mc.yandex.ru/watch/{i}" style="position:absolute;left:-9999px" alt="">' for i in ids)
    return (f'<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};'
            f'm[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})'
            f'(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");{inits}window.YM_IDS={json.dumps(ids)};</script>'
            f'<noscript><div>{noscript}</div></noscript>')


def area_served():
    places = [{"@type": "City", "name": "Волжский"}]
    for g in C.GEO:
        t = "City" if g["name"] in ("Краснослободск", "Дубовка", "Знаменск") else "AdministrativeArea"
        places.append({"@type": t, "name": g["name"],
                       "containedInPlace": {"@type": "AdministrativeArea", "name": g["region"]}})
    return places


def business_ld():
    ld = {
        "@context": "https://schema.org",
        "@type": "AutomotiveBusiness",
        "@id": URL + "/#business",
        "name": S["brand"],
        "url": URL + "/",
        "telephone": TEL,
        "image": URL + "/img/og.jpg",
        "logo": URL + "/img/icon-512.png",
        "openingHours": S["opening_hours_schema"],
        "priceRange": "от 1 200 ₽",
        "areaServed": area_served(),
        "description": "Эвакуатор в Волжском и районах Волгоградской области круглосуточно. Техника до 5 тонн, есть эвакуатор с кабиной на 5 пассажирских мест.",
    }
    if not is_todo("email"):
        ld["email"] = S["email"]
    if not is_todo("address"):
        ld["address"] = {"@type": "PostalAddress", "streetAddress": S["address"], "addressCountry": "RU"}
    return ld


def crumbs_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": URL + u} for i, (n, u) in enumerate(items)]}


def faq_ld(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}


def page(path, title, desc, body, ld=(), crumbs=None, noindex=False):
    """Полная HTML-страница. path — '/' или '/slug/'."""
    canonical = URL + path
    lds = list(ld)
    if crumbs:
        lds.append(crumbs_ld(crumbs))
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)
    crumbs_html = ""
    if crumbs:
        parts = [f'<a href="{u}">{esc(n)}</a>' for n, u in crumbs[:-1]] + [f'<span aria-current="page">{esc(crumbs[-1][0])}</span>']
        crumbs_html = f'<nav class="crumbs wrap" aria-label="Хлебные крошки">{" / ".join(parts)}</nav>'
    robots = '<meta name="robots" content="noindex, follow">' if noindex else ""
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="{esc(S["brand"])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{URL}/img/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#ffffff">
<meta name="yandex-verification" content="{S["yandex_verification"]}">
<link rel="icon" href="/img/favicon-32.png" type="image/png">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
<link rel="preload" href="/fonts/oswald-var-cyrillic.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/ptsans-400-cyrillic.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/css/style.css?v={ASSET_V}">
<script>document.documentElement.classList.add("js")</script>
{ld_html}
{metrika()}
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
{header()}
{crumbs_html}
<main id="main">
{body}
</main>
{footer()}
<script src="/js/main.js?v={ASSET_V}" defer></script>
</body>
</html>
'''


# ---------- блоки страниц ----------

def price_table(names=None, title=None):
    rows = []
    for g in S["prices"]:
        items = [it for it in g["items"] if names is None or it["name"] in names]
        if not items:
            continue
        if names is None:
            rows.append(f'<tr class="pt-group"><th colspan="2" scope="colgroup">{esc(g["group"])}</th></tr>')
        for it in items:
            name = esc(it["name"])
            if names is None and it.get("service"):
                name = f'<a href="/{SERVICES_BY_KEY[it["service"]]}/">{name}</a>'
            cls = ' class="free"' if it.get("free") else ""
            rows.append(f'<tr><td>{name}</td><td{cls}>{esc(it["price"])}</td></tr>')
    cap = f'<caption>{esc(title)}</caption>' if title else ""
    return f'<div class="table-wrap"><table class="price-table">{cap}<tbody>{"".join(rows)}</tbody></table></div>'


SERVICES_BY_KEY = {"moto": "perevozka-mototsiklov-kvadrotsiklov", "legkovye": "evakuaciya-legkovyh-avto",
                   "mezhgorod": "evakuator-mezhgorod", "pogruzka": "pogruzka-vygruzka-tehniki"}


def faq_block(faq, title="Частые вопросы", alt=False):
    items = "".join(f'<details class="faq-item"><summary><h3>{esc(q)}</h3></summary><p>{esc(a)}</p></details>' for q, a in faq)
    return f'<section class="section{" section-alt" if alt else ""}"><div class="wrap narrow"><h2>{esc(title)}</h2><div class="faq">{items}</div></div></section>'


def cta_band(text="Нужен эвакуатор прямо сейчас?"):
    return f'''<section class="cta-band"><div class="wrap cta-in">
  <div><p class="cta-title">{esc(text)}</p><p>Звоните круглосуточно — диспетчер сразу назовёт стоимость.</p></div>
  <div class="cta-actions">{tel_link("btn btn-call btn-lg")}</div>
</div></section>'''


def lead_form(context="Сайт"):
    endpoint = "" if is_todo("form_endpoint") else esc(S["form_endpoint"])
    if is_todo("form_endpoint"):
        TODOS.append(S["form_endpoint"]["todo"])
    return f'''<form class="lead-form" data-endpoint="{endpoint}" novalidate>
  <input type="hidden" name="page" value="{esc(context)}">
  <div class="hp" aria-hidden="true"><label>Не заполняйте <input name="website" tabindex="-1" autocomplete="off"></label></div>
  <label class="field"><span>Телефон*</span><input name="phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="+7 ___ ___-__-__" required></label>
  <label class="field"><span>Что и откуда везти</span><input name="comment" type="text" placeholder="Например: седан, Волжский → Ленинск"></label>
  <label class="consent"><input type="checkbox" name="consent" value="1" checked required> <span>Согласен на обработку персональных данных по <a href="/politika-konfidencialnosti/">политике конфиденциальности</a></span></label>
  <button class="btn btn-call" type="submit">Перезвоните мне</button>
  <p class="form-msg" role="status" aria-live="polite"></p>
</form>'''


def contact_block():
    return f'''<section class="section section-dark" id="zayavka"><div class="wrap contact-grid">
  <div>
    <h2>Вызвать эвакуатор</h2>
    <p class="lead">Быстрее всего — по телефону. Диспетчер на связи круглосуточно.</p>
    <p class="big-phone"><a href="tel:{TEL}" data-goal="call">{PHONE}</a></p>
    <div class="msg-row">{messenger_btn("whatsapp", "WhatsApp", "https://wa.me/{}")}{messenger_btn("telegram", "Telegram", "{}")}</div>
  </div>
  <div class="form-card"><p class="form-title">Или оставьте номер — перезвоним</p>{lead_form()}</div>
</div></section>'''


def why_block():
    items = [
        ("Свой эвакуатор в каждом районе", C.ASSIGNED),
        ("5 мест для пассажиров", C.SEATS),
        ("Техника до 5 тонн", "Легковые, мото и квадроциклы, тракторы, спецтехника, лодки и катера. Загружаем и выгружаем технику с грузовиков."),
        ("Документы для страховой", C.DOCS),
        ("Вызов бесплатно", "Платите только за перевозку. Стоимость диспетчер называет до выезда."),
        ("24/7, 365 дней в году", "Работаем ночью, в выходные и праздники."),
    ]
    cards = "".join(f'<li class="why-card"><span class="why-ico">{ICON_CHECK}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></li>' for t, d in items)
    return f'<section class="section"><div class="wrap"><h2>Почему звонят нам</h2><ul class="why-grid">{cards}</ul></div></section>'


def steps_block():
    steps = [
        ("Звоните", f"{S['phone_display']}, круглосуточно. Скажите, что везти, откуда и куда."),
        ("Узнаёте цену", "Диспетчер называет стоимость и отправляет ближайший эвакуатор."),
        ("Грузим и везём", "Надёжно крепим технику и везём. Пассажиры могут ехать в кабине — до 5 мест."),
    ]
    li = "".join(f'<li><span class="step-n">{i + 1}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></li>' for i, (t, d) in enumerate(steps))
    return f'<section class="section"><div class="wrap"><h2>Как вызвать эвакуатор</h2><ol class="steps">{li}</ol></div></section>'


def services_grid(exclude=None, title="Что перевозим"):
    cards = []
    for s in C.SERVICES:
        if s["slug"] == exclude:
            continue
        cards.append(f'<li><a class="svc-card" href="/{s["slug"]}/"><h3>{esc(s["nav"])}</h3>'
                     f'<p>{esc(s["short"])}</p><span class="svc-price">{esc(s["price_from"])}</span></a></li>')
    return f'<section class="section"><div class="wrap"><h2>{esc(title)}</h2><ul class="svc-grid">{"".join(cards)}</ul></div></section>'


def geo_grid(exclude=None, title="Где работаем"):
    cards = [f'<li><a class="geo-card" href="/">{ICON_PIN}<span><b>Волжский</b><small>Волгоградская область</small></span></a></li>']
    for g in C.GEO:
        if g["slug"] == exclude:
            continue
        cards.append(f'<li><a class="geo-card" href="/{g["slug"]}/">{ICON_PIN}<span><b>{esc(g["name"])}</b>'
                     f'<small>{esc(g["region"])}</small></span></a></li>')
    return (f'<section class="section section-alt"><div class="wrap"><h2>{esc(title)}</h2>'
            f'<p class="lead">{esc(C.ASSIGNED)}</p><ul class="geo-grid">{"".join(cards)}</ul></div></section>')


def gallery_block():
    items = [
        ("evakuaciya-traktorov", "Два трактора — два эвакуатора", "Два эвакуатора Hyundai HD78 с тракторами Беларус"),
        ("evakuaciya-traktora", "Трактор на платформе", "Зелёный трактор Zoomlion на красном эвакуаторе"),
    ]
    figs = "".join(f'<figure>{picture(n, alt, sizes="(max-width: 860px) 100vw, 33vw")}<figcaption>{esc(c)}</figcaption></figure>' for n, c, alt in items)
    return (f'<section class="section"><div class="wrap"><h2>Наши эвакуаторы в работе</h2>'
            f'<p class="lead">Уже помогли более {fact("clients_helped")} владельцам разной техники.</p>'
            f'<div class="gallery">{figs}</div></div></section>')


def fleet_block():
    return f'''<section class="section section-alt"><div class="wrap">
  <h2>Наши эвакуаторы</h2>
  <div class="fleet">
    <figure class="fleet-card">{picture("evakuator-5-mest", "Эвакуатор ГАЗель с двухрядной кабиной на 5 мест", sizes="(max-width: 860px) 100vw, 50vw")}
      <figcaption><b>5 пассажирских мест</b> Двухрядная кабина: семья или попутчики едут вместе с машиной — удобно и выгодно на межгороде.</figcaption></figure>
    <figure class="fleet-card">{picture("evakuator-5-tonn", "Эвакуатор Hyundai HD78 со сдвижной платформой", sizes="(max-width: 860px) 100vw, 50vw")}
      <figcaption><b>Груз до 5 тонн</b> Тракторы, спецтехника, внедорожники, лодки и катера — перевезём любую технику до 5 т.</figcaption></figure>
  </div>
</div></section>'''


def hero(h1, lead, img, img_alt, chips, eyebrow, bg=None):
    """bg=(имя, alt, подпись-источник) — фото на всю ширину с переходом в фон, как на plitka-volzhsky."""
    chips_html = "".join(f'<li>{ICON_CHECK}<span>{c}</span></li>' for c in chips)
    pic = picture(img, img_alt, sizes="(max-width: 860px) 100vw, 46vw", eager=True, cls="hero-img") if img else ""
    bg_html = credit = ""
    if bg:
        name, alt, credit = bg
        bg_html = f'<div class="hero-bg-img">{picture(name, alt, sizes="100vw", eager=True)}</div>'
        credit = f'<p class="hero-credit">{credit}</p>'
    cls = " hero-full" if bg else " hero-noimg" if not img else ""
    media_credit = f'<p class="hero-credit">{STOCK_CREDITS[img]}</p>' if img in STOCK_CREDITS else ""
    return f'''<section class="hero{cls}">{bg_html}<div class="wrap hero-in">
  <div class="hero-text">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{h1}</h1>
    <p class="hero-lead">{lead}</p>
    <ul class="chips">{chips_html}</ul>
    <div class="hero-actions">{tel_link("btn btn-call btn-lg")}{messenger_btn("whatsapp", "WhatsApp", "https://wa.me/{}")}</div>
    <p class="hero-note">Круглосуточно · вызов бесплатно</p>
  </div>
  {f'<div class="hero-media">{pic}{media_credit}</div>' if pic and not bg else ''}
</div>{credit}</section>'''


# стоковые фото и их обязательные подписи (лицензия CC BY-SA требует указать автора)
STOCK_CREDITS = {
    "evakuator-logan": 'Фото для примера · Cjp24, <a href="https://commons.wikimedia.org/wiki/File:Dacia_Logan_sur_d%C3%A9panneuse.jpg" '
                       'target="_blank" rel="noopener">Wikimedia Commons</a>, <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.ru" '
                       'target="_blank" rel="noopener">CC BY-SA 4.0</a>',
}


def stats_block():
    """Полоса цифр под первым экраном. Только факты с сайта; data-count — для анимации счёта."""
    items = [
        ('до <span data-count="5">5</span> т', "грузоподъёмность"),
        ('<span data-count="5">5</span> мест', "в кабине для пассажиров"),
        ('<em>24/7</em>', "без выходных и праздников"),
        ('<span data-count="8">8</span>', f"городов и районов, включая Знаменск"),
        ('от <span data-count="1200">1 200</span> ₽', "вызов бесплатно"),
    ]
    li = "".join(f"<li><b>{v}</b><span>{esc(t)}</span></li>" for v, t in items)
    return f'<section class="stats-band" aria-label="Коротко о нас"><ul class="wrap stats">{li}</ul></section>'


# ---------- страницы ----------

def home():
    faq = C.HOME_FAQ
    body = hero(
        "Эвакуатор в Волжском и районах области — круглосуточно",
        "Перевезём любую технику до 5 тонн: автомобили, мотоциклы, тракторы, лодки. "
        "Есть эвакуатор с кабиной на 5 мест — пассажиры едут вместе с машиной.",
        None, "",
        ["Вызов бесплатно", "Легковые от 1 500 ₽", "До 5 тонн", "До 5 пассажиров"],
        "Волжский · Ахтуба · Ленинск · Быково · Краснослободск · Дубовка · Горный Балыклей · Знаменск",
        bg=("hero-evakuator", "Эвакуатор с платформой везёт жёлтый спорткар по городу",
            'Фото для примера · <a href="https://commons.wikimedia.org/wiki/File:Moscow,_yellow_Porsche_on_a_red-white_Iveco,_May_2026_01.jpg" '
            'target="_blank" rel="noopener">Wikimedia Commons</a>, CC0'),
    )
    body += stats_block()
    body += services_grid()
    body += f'''<section class="section section-alt" id="ceny"><div class="wrap price-layout">
  <div><h2>Стоимость услуг</h2>
    <p class="lead"><b>Вызов эвакуатора — бесплатно.</b> Легковой автомобиль — от 1 500 ₽, мотоцикл и квадроцикл — от 1 200 ₽, межгород — от 70 ₽ за километр.</p>
    <p>Точную цену диспетчер назовёт по телефону до выезда — она зависит от массы техники, расстояния и того, заблокированы ли колёса.</p>
    {tel_link("btn btn-call")}
  </div>
  {price_table()}
</div></section>'''
    body += why_block()
    body += fleet_block()
    body += steps_block()
    body += geo_grid()
    body += gallery_block()
    body += f'''<section class="section section-alt"><div class="wrap narrow prose">
  <h2>Эвакуатор-34 — эвакуация техники в Волжском и области</h2>
  <p>Мы специализируемся на эвакуации любых транспортных средств массой до 5 тонн. Загружаем и выгружаем технику с грузовых автомобилей. Для удобства и экономии предоставляем эвакуаторы с 5 пассажирскими местами.</p>
  <p>{esc(C.DOCS)} Эвакуатор в кратчайшие сроки приедет к вашей машине и перевезёт её в любую точку России.</p>
  <p>{esc(C.ASSIGNED)} Работаем 7 дней в неделю, 365 дней в году.</p>
</div></section>'''
    body += faq_block(faq)
    body += contact_block()
    ld = [business_ld(), {"@context": "https://schema.org", "@type": "WebSite", "name": S["brand"], "url": URL + "/"}, faq_ld(faq)]
    return page("/", "Эвакуатор в Волжском круглосуточно — от 1 500 ₽ | Эвакуатор-34",
                "Эвакуатор в Волжском и районах: Средняя Ахтуба, Ленинск, Быково, Краснослободск, Дубовка, Знаменск. До 5 т, 5 мест в кабине, вызов бесплатно.",
                body, ld=ld)


def service_page(s):
    if s.get("draft"):
        DRAFTS.append(f'Тексты страницы /{s["slug"]}/')
    secs = ""
    for h, c in s["sections"]:
        inner = ("<ul class='ticks'>" + "".join(f"<li>{ICON_CHECK}<span>{esc(x)}</span></li>" for x in c) + "</ul>") if isinstance(c, list) else f"<p>{esc(c)}</p>"
        secs += f"<h2>{esc(h)}</h2>{inner}"
    extra_img = ""
    if s.get("img2"):
        extra_img = f'<figure class="inline-fig">{picture(s["img2"], s["img2_alt"], sizes="(max-width: 860px) 100vw, 50vw")}</figure>'
    body = hero(esc(s["h1"]), esc(s["lead"]), s["img"], s.get("img_alt", ""),
                [f"{esc(s['price_from'])}", "Вызов бесплатно", "До 5 тонн", "24/7"],
                "Волжский и районы области · 24/7")
    body += f'''<section class="section"><div class="wrap two-col">
  <div class="prose">{secs}{extra_img}</div>
  <div class="side-card"><h2 class="h3">Цены</h2>{price_table(s["price_keys"])}
    <p class="small muted">Окончательную стоимость диспетчер назовёт по телефону до выезда.</p>
    {tel_link("btn btn-call btn-block")}<p class="small"><a href="/tseny/">Все цены →</a></p></div>
</div></section>'''
    body += geo_grid(title=f'{s["nav"]}: где работаем')
    body += services_grid(exclude=s["slug"], title="Другие услуги")
    body += faq_block(s["faq"], alt=True)
    body += contact_block()
    service_ld = {
        "@context": "https://schema.org", "@type": "Service", "name": s["h1"], "serviceType": s["nav"],
        "provider": {"@id": URL + "/#business"}, "areaServed": area_served(),
        "offers": {"@type": "Offer", "priceCurrency": "RUB",
                   "price": re.sub(r"\D", "", s["price_from"].split("₽")[0]),
                   "description": s["price_from"]},
    }
    return page(f'/{s["slug"]}/', s["title"], s["desc"], body,
                ld=[business_ld(), service_ld, faq_ld(s["faq"])],
                crumbs=[("Главная", "/"), (s["nav"], f'/{s["slug"]}/')])


def geo_page(g):
    if g.get("draft"):
        DRAFTS.append(f'Тексты страницы /{g["slug"]}/')
    places = "".join(f"<li>{ICON_PIN}<span>{esc(p)}</span></li>" for p in g["places"])
    focus = "".join(f'<li><a class="svc-card" href="/{k}/"><h3>{esc(SERVICES[k]["nav"])}</h3><p>{esc(SERVICES[k]["short"])}</p>'
                    f'<span class="svc-price">{esc(SERVICES[k]["price_from"])}</span></a></li>' for k in g["services_focus"])
    related = " · ".join(f'<a href="/{r}/">{esc(GEO[r]["name"])}</a>' for r in g["related"])
    body = hero(esc(g["h1"]), esc(g["lead"]), "evakuator-logan" if g["slug"] != "evakuator-bykovo" else "evakuaciya-traktorov",
                "Синий седан на платформе эвакуатора" if g["slug"] != "evakuator-bykovo" else f'Эвакуатор {g["in"]}', ["Вызов бесплатно", "Легковые от 1 500 ₽", "До 5 тонн", "До 5 пассажиров"],
                f'{esc(g["name"])} · {esc(g["region"])} · 24/7')
    body += f'''<section class="section"><div class="wrap two-col">
  <div class="prose">
    <h2>Эвакуатор {esc(g["in"])}: что важно знать</h2>
    <p>{esc(g["about"])}</p>
    <h2>Куда приезжаем</h2>
    <ul class="places">{places}</ul>
    <p class="small muted">Не нашли свой населённый пункт? Позвоните — скорее всего, приедем и туда.</p>
    <p>Рядом работаем: {related}, <a href="/">Волжский</a>.</p>
  </div>
  <div class="side-card"><h2 class="h3">Цены {esc(g["in"])}</h2>{price_table(["Вызов эвакуатора", "Мотоциклы, квадроциклы", "Легковые автомобили", "От 1 500 кг", "От 3 000 кг", "Межгород, за 1 км"])}
    {tel_link("btn btn-call btn-block")}<p class="small"><a href="/tseny/">Все цены →</a></p></div>
</div></section>'''
    body += f'<section class="section section-alt"><div class="wrap"><h2>Чаще всего заказывают {esc(g["in"])}</h2><ul class="svc-grid">{focus}</ul></div></section>'
    body += why_block()
    body += faq_block(g["faq"] + [C.HOME_FAQ[2]], alt=True)
    body += contact_block()
    return page(f'/{g["slug"]}/', g["title"], g["desc"], body,
                ld=[business_ld(), faq_ld(g["faq"] + [C.HOME_FAQ[2]])],
                crumbs=[("Главная", "/"), (g["name"], f'/{g["slug"]}/')])


def prices_page():
    faq = [C.HOME_FAQ[0], C.HOME_FAQ[4],
           ("Сколько стоит эвакуатор в другой город?", "От 70 ₽ за километр пути. Точную сумму диспетчер назовёт, когда узнает маршрут и тип техники.")]
    body = f'''<section class="page-head"><div class="wrap">
  <h1>Цены на эвакуатор в Волжском и области</h1>
  <p class="hero-lead">Вызов эвакуатора бесплатный. Легковой автомобиль — от 1 500 ₽, мотоцикл и квадроцикл — от 1 200 ₽, спецтехника, сельхозтехника и водный транспорт — от 1 800 ₽ в зависимости от массы, межгород — от 70 ₽ за километр.</p>
</div></section>
<section class="section"><div class="wrap two-col">
  {price_table()}
  <div class="side-card"><h2 class="h3">От чего зависит цена</h2>
    <ul class="ticks">
      <li>{ICON_CHECK}<span>Тип и масса техники</span></li>
      <li>{ICON_CHECK}<span>Расстояние — по городу или межгород</span></li>
      <li>{ICON_CHECK}<span>Заблокированные колёса и руль</span></li>
      <li>{ICON_CHECK}<span>Погрузка с грузового автомобиля</span></li>
    </ul>
    <p>Окончательную стоимость диспетчер назовёт по телефону до выезда.</p>
    {tel_link("btn btn-call btn-block")}</div>
</div></section>'''
    body += services_grid(title="Услуги")
    body += faq_block(faq, alt=True)
    body += contact_block()
    offers = []
    for g in S["prices"]:
        for it in g["items"]:
            digits = re.sub(r"\D", "", it["price"])
            if digits:
                offers.append({"@type": "Offer", "name": it["name"], "priceCurrency": "RUB", "price": digits,
                               "description": it["price"]})
    catalog = {"@context": "https://schema.org", "@type": "OfferCatalog", "name": "Цены на эвакуатор", "itemListElement": offers}
    return page("/tseny/", "Цены на эвакуатор в Волжском — от 1 200 ₽, вызов бесплатно",
                "Прайс эвакуатора в Волжском и области: легковые от 1 500 ₽, мото от 1 200 ₽, спецтехника по массе от 1 800 ₽, межгород от 70 ₽/км.",
                body, ld=[business_ld(), catalog, faq_ld(faq)], crumbs=[("Главная", "/"), ("Цены", "/tseny/")])


def contacts_page():
    body = f'''<section class="page-head"><div class="wrap">
  <h1>Контакты</h1>
  <p class="hero-lead">Вызвать эвакуатор: <a href="tel:{TEL}" data-goal="call">{PHONE}</a>. Работаем круглосуточно, без выходных, в Волжском, районах Волгоградской области и в Знаменске.</p>
</div></section>
<section class="section"><div class="wrap two-col">
  <dl class="contacts-dl">
    <dt>Телефон</dt><dd><a href="tel:{TEL}" data-goal="call">{PHONE}</a></dd>
    <dt>Режим работы</dt><dd>{esc(S["hours"])}</dd>
    <dt>WhatsApp</dt><dd>{messenger_btn("whatsapp", "Написать", "https://wa.me/{}", cls="link")}</dd>
    <dt>Telegram</dt><dd>{messenger_btn("telegram", "Написать", "{}", cls="link")}</dd>
    <dt>E-mail</dt><dd>{fact("email")}</dd>
    <dt>Адрес</dt><dd>{fact("address")}</dd>
    <dt>Реквизиты</dt><dd>{fact("legal_name")}, ИНН {fact("inn")}, {fact("ogrn")}</dd>
  </dl>
  <div class="form-card form-card-light"><p class="form-title">Оставьте номер — перезвоним</p>{lead_form("Контакты")}</div>
</div></section>'''
    body += geo_grid()
    return page("/kontakty/", "Контакты — Эвакуатор-34, Волжский, 8 (927) 067-70-70",
                "Телефон эвакуатора в Волжском: 8 (927) 067-70-70, круглосуточно. Работаем в районах Волгоградской области и в Знаменске.",
                body, ld=[business_ld()], crumbs=[("Главная", "/"), ("Контакты", "/kontakty/")])


def privacy_page():
    body = f'''<section class="page-head"><div class="wrap narrow"><h1>Политика конфиденциальности</h1></div></section>
<section class="section"><div class="wrap narrow prose">
<p>Политика составлена в соответствии с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных» и описывает, как обрабатываются персональные данные посетителей сайта {esc(S["domain_display"])}.</p>
<h2>1. Оператор</h2>
<p>Оператор персональных данных: {fact("legal_name")}, ИНН {fact("inn")}, {fact("ogrn")}. Адрес: {fact("address")}. E-mail: {fact("email")}. Телефон: {PHONE}.</p>
<h2>2. Какие данные мы получаем</h2>
<p>Номер телефона и, по желанию, комментарий о том, что и откуда нужно перевезти, — если вы оставляете заявку в форме на сайте. Технические данные (cookie, IP-адрес, сведения о браузере и действиях на сайте) — через сервис Яндекс Метрика.</p>
<h2>3. Зачем</h2>
<p>Чтобы перезвонить вам, рассчитать стоимость и выполнить перевозку, а также чтобы анализировать посещаемость и делать сайт удобнее.</p>
<h2>4. Правовое основание</h2>
<p>Ваше согласие, которое вы даёте, отмечая флажок в форме заявки, а также необходимость исполнения договора, стороной которого вы являетесь.</p>
<h2>5. Сроки хранения</h2>
<p>Данные заявки хранятся не дольше, чем нужно для её выполнения, и не более 1 года, после чего удаляются. Вы можете отозвать согласие раньше — данные будут удалены в течение 30 дней.</p>
<h2>6. Передача третьим лицам</h2>
<p>Мы не продаём и не передаём ваши данные третьим лицам, кроме случаев, предусмотренных законом. Статистические данные обрабатывает ООО «Яндекс» в рамках сервиса Яндекс Метрика.</p>
<h2>7. Cookie</h2>
<p>Сайт использует cookie, чтобы корректно работать, и сервис Яндекс Метрика — чтобы анализировать посещаемость. Отключить cookie можно в настройках браузера.</p>
<h2>8. Ваши права</h2>
<p>Вы вправе узнать, какие данные о вас обрабатываются, потребовать их уточнения или удаления, отозвать согласие. Напишите на {fact("email")} или позвоните {PHONE}.</p>
<p class="small muted">Редакция от {TODAY}.</p>
</div></section>'''
    return page("/politika-konfidencialnosti/", "Политика конфиденциальности — Эвакуатор-34",
                "Как сайт эвакуатор-34.рф обрабатывает персональные данные и cookie в соответствии с 152-ФЗ.",
                body, crumbs=[("Главная", "/"), ("Политика конфиденциальности", "/politika-konfidencialnosti/")])


def not_found_page():
    body = f'''<section class="page-head page-404"><div class="wrap narrow">
  <h1>Страница не найдена</h1>
  <p class="hero-lead">Такой страницы нет, но эвакуатор есть — круглосуточно.</p>
  <div class="hero-actions">{tel_link("btn btn-call btn-lg")}<a class="btn btn-ghost" href="/">На главную</a></div>
</div></section>'''
    return page("/404.html", "Страница не найдена — Эвакуатор-34", "Страница не найдена.", body, noindex=True)


# ---------- служебные файлы ----------

def robots_txt():
    if STAGING:
        return "User-agent: *\nDisallow: /\n"
    return f"""User-agent: *
Allow: /
Disallow: /404.html

Sitemap: {URL}/sitemap.xml
"""


def sitemap_xml(paths):
    urls = "".join(f"<url><loc>{URL}{p}</loc><lastmod>{TODAY}</lastmod></url>" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'


def llms_txt():
    lines = [f"# {S['brand']} — эвакуатор в Волжском и районах Волгоградской области", "",
             f"> Эвакуация техники массой до 5 тонн круглосуточно. Есть эвакуатор с кабиной на 5 пассажирских мест. Вызов бесплатно. Телефон {S['phone_display']}.", "",
             "## Цены"]
    for g in S["prices"]:
        for it in g["items"]:
            lines.append(f"- {g['group']}: {it['name']} — {it['price']}")
    lines += ["", "## Услуги"] + [f"- [{s['nav']}]({URL}/{s['slug']}/): {s['price_from']}" for s in C.SERVICES]
    lines += ["", "## География", f"- [Волжский]({URL}/)"] + [f"- [{g['name']}]({URL}/{g['slug']}/) — {g['region']}" for g in C.GEO]
    lines += ["", "## Контакты", f"- Телефон: {S['phone_display']}", f"- Режим работы: {S['hours']}", f"- [Контакты]({URL}/kontakty/)", ""]
    return "\n".join(lines)


def htaccess():
    return f"""# Apache: эвакуатор-34.рф
Options -Indexes
DirectorySlash Off
ErrorDocument 404 /404.html
AddDefaultCharset utf-8

RewriteEngine On
# http → https. Если TLS снимает nginx перед Apache (REG.RU, Beget), %{{HTTPS}} всегда off,
# поэтому смотрим ещё X-Forwarded-Proto — иначе бесконечный редирект.
# После заливки проверить curl -I (см. README); при петле закомментировать эти 3 строки
# и включить редирект на HTTPS в панели хостинга.
RewriteCond %{{HTTPS}} !=on
RewriteCond %{{HTTP:X-Forwarded-Proto}} !https
RewriteRule ^(.*)$ {URL}/$1 [R=301,L]
# www → без www
RewriteCond %{{HTTP_HOST}} ^www\\. [NC]
RewriteRule ^(.*)$ {URL}/$1 [R=301,L]

# дубли главной со старого конструктора
RewriteCond %{{THE_REQUEST}} \\s/index\\.(php|html)[\\s?] [NC]
RewriteRule ^ {URL}/ [R=301,L]

# каталог без слеша → со слешем, сразу на https
RewriteCond %{{REQUEST_FILENAME}} -d
RewriteRule ^(.*[^/])$ {URL}/$1/ [R=301,L]
DirectoryIndex index.html

<IfModule mod_headers.c>
  Header always set Strict-Transport-Security "max-age=31536000"
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header unset X-Powered-By
  <FilesMatch "\\.(webp|jpg|png|woff2)$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
  <FilesMatch "\\.(css|js)$">
    Header set Cache-Control "public, max-age=2592000"
  </FilesMatch>
</IfModule>
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css application/javascript text/plain application/xml image/svg+xml
</IfModule>
"""


# ---------- сборка ----------

def main():
    global ASSET_V
    # шрифты подключаем внутри style.css
    css = (SRC / "fonts" / "fonts.css").read_text(encoding="utf-8") + (SRC / "css" / "style.css").read_text(encoding="utf-8")
    ASSET_V = hashlib.md5((css + (SRC / "js" / "main.js").read_text(encoding="utf-8")).encode()).hexdigest()[:8]

    # сначала всё рендерим в память — продакшен-сборка с пробелами ничего не пишет на диск
    pages = {"/": home()}
    for s in C.SERVICES:
        pages[f'/{s["slug"]}/'] = service_page(s)
    for g in C.GEO:
        pages[f'/{g["slug"]}/'] = geo_page(g)
    pages["/tseny/"] = prices_page()
    pages["/kontakty/"] = contacts_page()
    pages["/politika-konfidencialnosti/"] = privacy_page()
    files = {
        "404.html": not_found_page(), "robots.txt": robots_txt(), "sitemap.xml": sitemap_xml(pages.keys()),
        "llms.txt": llms_txt(), ".htaccess": htaccess(),
    }

    todos = sorted(set(TODOS))
    drafts = sorted(set(DRAFTS))
    if todos or drafts:
        print("Нужно от клиента:")
        for t in todos:
            print("  •", t)
        print("\nСверить с клиентом (черновые тексты):")
        for d in drafts:
            print("  •", d)
        if PROD:
            print("\nПродакшен-сборка остановлена, dist/ не тронут: заполните todo и снимите draft в data/site.json и content.py.")
            sys.exit(1)
        print()

    DIST.mkdir(exist_ok=True)
    for p in DIST.iterdir():  # чистим содержимое, саму папку может держать локальный сервер
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    for sub in ("css", "js", "img", "fonts"):
        shutil.copytree(SRC / sub, DIST / sub)
    # старые фото — по прежним адресам (могут быть в Яндекс Картинках)
    shutil.copytree(ROOT / "_old_site" / "gallery_gen", DIST / "gallery_gen")
    (DIST / "css" / "style.css").write_text(css, encoding="utf-8")
    (DIST / "fonts" / "fonts.css").unlink()
    for path, doc in pages.items():
        out = DIST / path.strip("/") / "index.html" if path != "/" else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(staging_html(doc), encoding="utf-8")
    for name, text in files.items():
        (DIST / name).write_text(staging_html(text) if name.endswith(".html") else text, encoding="utf-8")
    if BASE:
        (DIST / "css" / "style.css").write_text(css.replace("url(/fonts/", f"url({BASE}/fonts/"), encoding="utf-8")
    mode = "продакшен" if PROD else "превью (noindex, без Метрики)" if STAGING else "черновик"
    print(f"Собрано страниц: {len(pages)} + 404 → {DIST} ({mode})")


def staging_html(doc):
    """Превью: закрыть от индексации и, если сайт лежит в подпапке, добавить префикс к путям."""
    if not STAGING:
        return doc
    doc = doc.replace('<meta name="robots" content="noindex, follow">', "")
    doc = doc.replace("<head>\n", '<head>\n<meta name="robots" content="noindex, nofollow">\n', 1)
    if BASE:
        doc = re.sub(r'((?:href|src)=")/(?!/)', rf"\1{BASE}/", doc)
        doc = re.sub(r'srcset="([^"]*)"', lambda m: 'srcset="' + re.sub(r"(^|, )/", rf"\1{BASE}/", m.group(1)) + '"', doc)
    return doc


ASSET_V = "dev"
if __name__ == "__main__":
    main()
