/* ============================================================
   LAZZA — логика меню, корзины, языков и отправки заказа
   ============================================================ */

(function () {
  'use strict';

  /* ---------- мелкие помощники ---------- */

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  const round2 = (n) => Math.round(n * 100) / 100;

  const store = {
    get(key, fallback) {
      try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
      } catch (e) { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* приватный режим */ }
    },
  };

  /* ---------- язык ---------- */

  const LANG_CODES = LANGS.map((l) => l.code);

  function detectLang() {
    const fromUrl = new URLSearchParams(location.search).get('lang');
    if (fromUrl && LANG_CODES.indexOf(fromUrl) > -1) return fromUrl;

    const saved = store.get('lazza_lang_v1', null);
    if (saved && LANG_CODES.indexOf(saved) > -1) return saved;

    const nav = (navigator.languages || [navigator.language || '']).join(',').toLowerCase();
    if (nav.indexOf('az') === 0 || nav.indexOf(',az') > -1) return 'az';
    if (nav.indexOf('ru') > -1) return 'ru';
    if (nav.indexOf('en') > -1) return 'en';

    return CONFIG.defaultLang;
  }

  let lang = detectLang();

  /* ---------- тема ---------- */

  const systemLight = () => window.matchMedia('(prefers-color-scheme: light)').matches;

  /* 'dark' | 'light' | 'auto' — выбор гостя, иначе настройка кафе */
  let skinPref = store.get('lazza_skin_v1', null) || CONFIG.defaultTheme || 'dark';
  if (['dark', 'light', 'auto'].indexOf(skinPref) < 0) skinPref = 'dark';

  const skinNow = () => (skinPref === 'auto' ? (systemLight() ? 'light' : 'dark') : skinPref);

  function applySkin() {
    const skin = skinNow();
    document.documentElement.setAttribute('data-skin', skin);

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = skin === 'light' ? '#f4efe5' : '#16100d';

    /* иконка показывает, куда переключит нажатие */
    const goingLight = skin === 'dark';
    const label = goingLight ? t('themeLight') : t('themeDark');

    $$('.skin').forEach((btn) => {
      btn.innerHTML = '<svg aria-hidden="true"><use href="#i-' + (goingLight ? 'sun' : 'moon') + '"/></svg>';
      btn.setAttribute('aria-label', label);
      btn.title = label;
    });
  }

  function toggleSkin() {
    skinPref = skinNow() === 'light' ? 'dark' : 'light';
    store.set('lazza_skin_v1', skinPref);
    applySkin();
  }
  const meta = () => LANGS.find((l) => l.code === lang);

  /* строка интерфейса; {placeholder} подставляется из params */
  function t(key, params) {
    let s = I18N[lang][key];
    if (s === undefined) s = I18N[CONFIG.defaultLang][key];
    if (typeof s !== 'string') return s;
    if (params) {
      Object.keys(params).forEach((k) => { s = s.split('{' + k + '}').join(params[k]); });
    }
    return s;
  }

  /* локализованное поле данных: L(item.name) */
  const L = (field) => (field && typeof field === 'object' ? (field[lang] || field[CONFIG.defaultLang]) : field);

  /* число в формате выбранного языка: 1.234,50 / 1 234,50 / 1,234.50 */
  function num(n, digits) {
    const m = meta();
    const parts = Math.abs(n).toFixed(digits === undefined ? 0 : digits).split('.');
    const int = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, m.grp);
    return (n < 0 ? '-' : '') + int + (parts[1] ? m.dec + parts[1] : '');
  }

  const money = (n) => num(round2(n), 2) + ' ' + CONFIG.currency;

  function plural(n, forms) {
    if (lang === 'az') return forms[0];
    if (lang === 'ru') {
      const a = Math.abs(n) % 100, b = a % 10;
      if (a > 10 && a < 20) return forms[2];
      if (b > 1 && b < 5) return forms[1];
      if (b === 1) return forms[0];
      return forms[2];
    }
    return n === 1 ? forms[0] : forms[1];
  }

  /* Intl для az даёт «M08» вместо названия месяца, поэтому собираем дату сами */
  function dateText(iso) {
    const d = new Date(iso + 'T12:00:00');
    if (isNaN(d.getTime())) return iso;
    const month = t('months')[d.getMonth()];
    return lang === 'en' ? month + ' ' + d.getDate() : d.getDate() + ' ' + month;
  }

  function stamp(withYear) {
    const d = new Date();
    const p = (n) => String(n).padStart(2, '0');
    const date = p(d.getDate()) + '.' + p(d.getMonth() + 1) + (withYear ? '.' + d.getFullYear() : '');
    return date + ', ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  function weightText(w) {
    if (!w) return '';
    const units = t('units');
    return num(w.v, w.v % 1 ? 1 : 0) + ' ' + (units[w.u] || w.u);
  }

  /* ---------- состояние ---------- */

  const ITEMS = {};
  MENU.forEach((cat) => cat.items.forEach((it) => { ITEMS[it.id] = it; }));

  /* строка корзины: { key, id, qty, mods: [[индекс группы, индекс варианта]] } */
  function validLine(line) {
    const item = ITEMS[line.id];
    if (!item || !Array.isArray(line.mods) || !(line.qty > 0)) return false;
    return line.mods.every((pair) => {
      const group = (item.mods || [])[pair[0]];
      return group && group.choices[pair[1]];
    });
  }

  let cart = (store.get('lazza_cart_v1', []) || []).filter(validLine);
  let reviews = store.get('lazza_reviews_v1', []) || [];
  let deliveryMode = store.get('lazza_mode_v1', 'table') || 'table';
  const tableNo = new URLSearchParams(location.search).get('table') || '';

  let orderNo = sessionStorage.getItem('lazza_order_no');
  if (!orderNo) {
    orderNo = 'A-' + String(Math.floor(Math.random() * 9000) + 1000);
    try { sessionStorage.setItem('lazza_order_no', orderNo); } catch (e) { /* ignore */ }
  }

  const saveCart = () => store.set('lazza_cart_v1', cart);

  /* цена и состав строки считаются из меню, поэтому язык и цены всегда свежие */
  function lineItem(line) { return ITEMS[line.id]; }

  function lineChoices(line) {
    const item = lineItem(line);
    return line.mods.map((pair) => {
      const group = item.mods[pair[0]];
      return { group: L(group.title), choice: group.choices[pair[1]] };
    });
  }

  function lineUnit(line) {
    return round2(lineItem(line).price +
      lineChoices(line).reduce((s, m) => s + m.choice.price, 0));
  }

  /* ============================================================
     ШАПКА, ПОДВАЛ, ЯЗЫКИ
     ============================================================ */

  function isOpenNow() {
    const h = new Date().getHours();
    return CONFIG.openTo > CONFIG.openFrom
      ? h >= CONFIG.openFrom && h < CONFIG.openTo
      : h >= CONFIG.openFrom || h < CONFIG.openTo;
  }

  const pad2 = (n) => String(n).padStart(2, '0');

  function renderStatics() {
    document.documentElement.lang = lang;
    document.title = CONFIG.name + ' — ' + t('menuLabel');

    $('#tagline').textContent = t('tagline');
    $('#scrollHint').textContent = t('scrollHint');
    $('#tableTag').textContent = tableNo ? t('tableLabel', { n: tableNo }) : t('menuLabel');

    const open = isOpenNow();
    $('#statusText').textContent = open
      ? t('statusOpen', { h: pad2(CONFIG.openTo) })
      : t('statusClosed', { h: pad2(CONFIG.openFrom) });
    $('#statusLine').classList.toggle('status--closed', !open);

    /* контакты */
    const tel = 'tel:' + CONFIG.phone.replace(/[^\d+]/g, '');
    const insta = 'https://instagram.com/' + CONFIG.instagram;

    $('#phoneChip').href = tel;
    $('#phoneText').textContent = CONFIG.phone;
    $('#phoneChip').setAttribute('aria-label', t('callAction') + ': ' + CONFIG.phone);

    $('#instaChip').href = insta;
    $('#instaText').textContent = '@' + CONFIG.instagram;

    const addr = L(CONFIG.address) + ', ' + L(CONFIG.city);
    $('#addressChip').href = CONFIG.mapUrl;
    $('#addressText').textContent = addr;

    /* подвал */
    $('#footWhere').textContent = t('footWhere');
    $('#footContact').textContent = t('footContact');
    $('#footAddress').textContent = addr;
    $('#footAddress').href = CONFIG.mapUrl;
    $('#footHours').textContent = L(CONFIG.hours);
    $('#footPhone').textContent = CONFIG.phone;
    $('#footPhone').href = tel;
    $('#footWa').textContent = t('footWa');
    $('#footWa').href = 'https://wa.me/' + CONFIG.whatsapp;
    $('#footInsta').textContent = t('footInsta');
    $('#footInsta').href = insta;
    $('#footNote').textContent = t('footNote');

    /* корзина и формы */
    $('#cartLabel').textContent = t('showOrder');
    $('#receiptTitle').textContent = CONFIG.name.toUpperCase();
    $('#receiptSub').textContent = L(CONFIG.address) + ' · ' + t('receiptSub');
    $('#receiptNo').textContent = '№ ' + orderNo;

    $('#tPositionsLabel').textContent = t('rPositions');
    $('#tSubtotalLabel').textContent = t('rSubtotal');
    $('#tDeliveryLabel').textContent = t('rDelivery');
    $('#tGrandLabel').textContent = t('rTotal');

    $('#howToGet').textContent = t('howToGet');
    $('[data-mode="table"]').textContent = t('segTable');
    $('[data-mode="pickup"]').textContent = t('segPickup');
    $('[data-mode="delivery"]').textContent = t('segDelivery');

    const fields = [
      ['#fTable', 'iTable', 'fTable', 'phTable', 'eTable'],
      ['#fAddress', 'iAddress', 'fAddress', 'phAddress', 'eAddress'],
      ['#fName', 'iName', 'fName', 'phName', 'eName'],
      ['#fPhone', 'iPhone', 'fPhone', 'phPhone', 'ePhone'],
      ['#fNote', 'iNote', 'fNote', 'phNote', null],
      ['#fRName', 'iRName', 'fRName', 'phRName', 'eRName'],
      ['#fRText', 'iRText', 'fRText', 'phRText', 'eRText'],
    ];

    fields.forEach((f) => {
      const box = $(f[0]);
      $('label', box).textContent = t(f[2]);
      $('#' + f[1]).placeholder = t(f[3]);
      if (f[4]) $('.field__err', box).textContent = t(f[4]);
    });

    $('#sendOrderText').textContent = t('sendOrder');

    /* отзывы */
    $('#reviewsEyebrow').textContent = t('reviewsEyebrow');
    $('#reviewsTitle').textContent = t('reviewsTitle');
    $('#openReviewText').textContent = t('writeReview');
    $('#reviewTitle').textContent = t('reviewTitle');
    $('#reviewSub').textContent = t('reviewSub');
    $('#fRatingLabel').textContent = t('fRating');
    $('#sendReviewText').textContent = t('sendReview');
    $('#detailAddText').textContent = t('addToOrder');
    applySkin();
  }

  function renderLangs() {
    const html = LANGS.map((l) => (
      '<button class="lang" type="button" data-lang="' + l.code + '"' +
        ' aria-pressed="' + (l.code === lang) + '"' +
        ' lang="' + l.code + '" title="' + esc(l.name) + '">' + l.label + '</button>'
    )).join('');
    $$('.langs').forEach((box) => { box.innerHTML = html; });
  }

  function setLang(code) {
    if (code === lang || LANG_CODES.indexOf(code) < 0) return;
    lang = code;
    store.set('lazza_lang_v1', code);

    renderLangs();
    renderStatics();
    renderMenu();
    renderReviews();
    renderStarPick();
    updateBar();
    renderReceipt();
    if (draft) refreshDetail();
    setupScrollSpy();
  }

  /* ============================================================
     РЕНДЕР МЕНЮ
     ============================================================ */

  const iconPlus = '<svg aria-hidden="true"><use href="#i-plus"/></svg>';
  const iconMinus = '<svg aria-hidden="true"><use href="#i-minus"/></svg>';

  function qtyOf(id) {
    return cart.reduce((sum, line) => (line.id === id ? sum + line.qty : sum), 0);
  }

  function controlsHTML(item) {
    const qty = qtyOf(item.id);
    const hasMods = !!(item.mods && item.mods.length);
    const name = L(item.name);

    if (qty > 0 && !hasMods) {
      return (
        '<div class="stepper" data-id="' + item.id + '">' +
          '<button type="button" data-act="dec" aria-label="' + esc(t('decAria', { name: name })) + '">' + iconMinus + '</button>' +
          '<span class="stepper__n">' + qty + '</span>' +
          '<button type="button" data-act="inc" aria-label="' + esc(t('incAria', { name: name })) + '">' + iconPlus + '</button>' +
        '</div>'
      );
    }

    const label = qty > 0 ? t('addMoreAria', { n: qty, name: name }) : t('addAria', { name: name });

    return (
      '<button class="add" type="button" data-act="add" data-id="' + item.id + '" aria-label="' + esc(label) + '">' +
        (qty > 0 ? '<span class="add__n">' + qty + '</span>' : iconPlus) +
      '</button>'
    );
  }

  function cardHTML(item) {
    const badgeClass = item.tag === 'new' ? ' badge--new' : (item.tag === 'deal' ? ' badge--deal' : '');
    const tagText = item.tag ? t('tags')[item.tag] : '';

    return (
      '<article class="card' + (item.tag ? ' card--feature' : '') + '" data-card="' + item.id + '">' +
        '<div class="card__media">' +
          (item.tag ? '<span class="badge' + badgeClass + '">' + esc(tagText) + '</span>' : '') +
          (item.model ? '<span class="chip3d">' + esc(t('ar3dBadge')) + '</span>' : '') +
          '<img src="' + item.img + '" alt="' + esc(L(item.name)) + '" loading="lazy" decoding="async">' +
        '</div>' +
        '<div class="card__body">' +
          '<h3 class="card__name"><button class="card__open" type="button" data-id="' + item.id + '">' +
            esc(L(item.name)) + '</button></h3>' +
          '<p class="card__desc">' + esc(L(item.desc)) + '</p>' +
          '<div class="card__foot">' +
            '<span class="price">' + money(item.price) +
              (item.old ? '<span class="price__old">' + money(item.old) + '</span>' : '') +
            '</span>' +
            controlsHTML(item) +
          '</div>' +
        '</div>' +
      '</article>'
    );
  }

  function renderMenu() {
    $('#menuRoot').innerHTML = MENU.map((cat) => (
      '<section class="section" id="' + cat.id + '">' +
        '<div class="section__head">' +
          '<p class="section__eyebrow">' + cat.items.length + ' ' +
            esc(plural(cat.items.length, t('positions'))) + '</p>' +
          '<h2 class="section__title">' + esc(L(cat.title)) + '</h2>' +
          (cat.note ? '<p class="section__note">' + esc(L(cat.note)) + '</p>' : '') +
        '</div>' +
        '<div class="grid">' + cat.items.map(cardHTML).join('') + '</div>' +
      '</section>'
    )).join('');

    $('#navScroll').innerHTML = MENU.map((cat) => (
      '<button class="nav__btn" type="button" data-goto="' + cat.id + '">' + esc(L(cat.title)) + '</button>'
    )).join('') +
      '<button class="nav__btn nav__btn--reviews" type="button" data-goto="reviews">' +
        esc(t('navReviews')) + '</button>';
  }

  function refreshCard(id) {
    const card = $('[data-card="' + id + '"]');
    if (!card) return;
    const old = $('.add, .stepper', card);
    if (old) old.outerHTML = controlsHTML(ITEMS[id]);
  }

  function refreshAllCards() {
    Object.keys(ITEMS).forEach(refreshCard);
  }

  /* ============================================================
     КОРЗИНА
     ============================================================ */

  const lineKey = (id, mods) => id + '|' + mods.map((p) => p[0] + ':' + p[1]).join(',');

  function addToCart(item, mods, qty) {
    const key = lineKey(item.id, mods);
    const found = cart.find((l) => l.key === key);

    if (found) found.qty += qty;
    else cart.push({ key: key, id: item.id, qty: qty, mods: mods });

    saveCart();
    updateBar(true);
    refreshCard(item.id);
    toast(t('tAdded', { name: L(item.name) }));
  }

  function changeLine(key, delta) {
    const i = cart.findIndex((l) => l.key === key);
    if (i < 0) return;
    cart[i].qty += delta;
    const id = cart[i].id;
    if (cart[i].qty <= 0) cart.splice(i, 1);
    saveCart();
    updateBar();
    refreshCard(id);
    renderReceipt();
  }

  function quickAdd(item, delta) {
    const key = lineKey(item.id, []);
    const found = cart.find((l) => l.key === key);

    if (!found && delta > 0) cart.push({ key: key, id: item.id, qty: 1, mods: [] });
    else if (found) {
      found.qty += delta;
      if (found.qty <= 0) cart = cart.filter((l) => l.key !== key);
    }

    saveCart();
    updateBar(delta > 0);
    refreshCard(item.id);
  }

  const cartCount = () => cart.reduce((s, l) => s + l.qty, 0);
  const cartSubtotal = () => round2(cart.reduce((s, l) => s + lineUnit(l) * l.qty, 0));

  function deliveryCost() {
    if (deliveryMode !== 'delivery') return 0;
    return cartSubtotal() >= CONFIG.freeDeliveryFrom ? 0 : CONFIG.deliveryFee;
  }

  function updateBar(bump) {
    const n = cartCount();
    const bar = $('#cartBar');
    $('#cartCount').textContent = n;
    $('#cartSum').textContent = money(cartSubtotal());
    bar.classList.toggle('is-visible', n > 0);

    if (bump && n > 0) {
      bar.classList.remove('is-bump');
      void bar.offsetWidth;
      bar.classList.add('is-bump');
      setTimeout(() => bar.classList.remove('is-bump'), 500);
    }
  }

  /* ============================================================
     ЛИСТ БЛЮДА
     ============================================================ */

  let draft = null;

  function selectedMods() {
    const groups = draft.item.mods || [];
    const out = [];
    groups.forEach((group, gi) => {
      (draft.picked[gi] || []).forEach((ci) => out.push([gi, ci]));
    });
    return out;
  }

  function draftUnit() {
    const groups = draft.item.mods || [];
    return round2(draft.item.price + selectedMods()
      .reduce((s, pair) => s + groups[pair[0]].choices[pair[1]].price, 0));
  }

  function openDetail(id) {
    const item = ITEMS[id];
    if (!item) return;

    draft = { item: item, qty: 1, picked: {} };
    (item.mods || []).forEach((g, gi) => {
      draft.picked[gi] = (g.type === 'single' && g.required && g.choices.length) ? [0] : [];
    });

    refreshDetail();
    openSheet($('#detailSheet'));
  }

  /* перерисовывает открытый лист — используется и при смене языка */
  function refreshDetail() {
    const item = draft.item;

    $('#detailImg').src = item.img;
    $('#detailImg').alt = L(item.name);
    $('#detailName').textContent = L(item.name);
    $('#detailDesc').textContent = L(item.desc);

    const facts = [];
    if (item.weight) facts.push(weightText(item.weight));
    if (item.kcal) facts.push(t('kcal', { n: item.kcal }));
    facts.push(t('basePrice', { p: money(item.price) }));
    $('#detailFacts').innerHTML = facts.map((f) => '<span class="fact">' + esc(f) + '</span>').join('');

    $('#detailMods').innerHTML = (item.mods || []).map((g, gi) => (
      '<div class="modgroup">' +
        '<p class="modgroup__title">' + esc(L(g.title)) +
          '<span class="modgroup__hint">' + esc(g.type === 'multi' ? t('chooseMany') : t('chooseOne')) + '</span>' +
        '</p>' +
        '<div class="modlist">' + g.choices.map((c, ci) => (
          '<label class="mod">' +
            '<input type="' + (g.type === 'multi' ? 'checkbox' : 'radio') + '"' +
              ' name="mod-' + gi + '" value="' + ci + '" data-group="' + gi + '"' +
              ((draft.picked[gi] || []).indexOf(ci) > -1 ? ' checked' : '') + '>' +
            '<span class="mod__box' + (g.type === 'multi' ? ' mod__box--sq' : '') + '">' +
              '<svg aria-hidden="true"><use href="#i-check"/></svg></span>' +
            '<span class="mod__name">' + esc(L(c.name)) + '</span>' +
            '<span class="mod__price">' + (c.price ? '+ ' + money(c.price) : esc(t('noExtra'))) + '</span>' +
          '</label>'
        )).join('') + '</div>' +
      '</div>'
    )).join('');

    $('#qtyN').textContent = draft.qty;
    $('#qtyMinus').disabled = draft.qty <= 1;
    updateDetailSum();

    if (window.LazzaAR) window.LazzaAR.sync(item, t);
  }

  function updateDetailSum() {
    $('#detailSum').textContent = money(draftUnit() * draft.qty);
  }

  /* ============================================================
     ЧЕК
     ============================================================ */

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let x = Math.imul(a ^ (a >>> 15), 1 | a);
      x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  }

  function drawBarcode() {
    let seed = 0;
    for (let i = 0; i < orderNo.length; i++) seed = seed * 31 + orderNo.charCodeAt(i);
    const rnd = mulberry32(seed);
    const stops = [];
    let x = 0;
    while (x < 100) {
      const w = 0.45 + rnd() * 1.5;
      stops.push('#221b16 ' + x + '% ' + Math.min(x + w, 100) + '%');
      x += w;
      const gap = 0.5 + rnd() * 1.5;
      stops.push('transparent ' + x + '% ' + Math.min(x + gap, 100) + '%');
      x += gap;
    }
    $('#barcode').style.backgroundImage = 'linear-gradient(90deg,' + stops.join(',') + ')';
    $('#barcodeId').textContent = orderNo.replace('-', ' ') + ' ' + CONFIG.name.toUpperCase();
  }

  function renderReceipt() {
    const box = $('#receiptItems');
    const n = cartCount();

    $('#receiptDate').textContent = stamp(true);

    if (!n) {
      box.innerHTML =
        '<div class="empty">' +
          '<p class="empty__title">' + esc(t('emptyTitle')) + '</p>' +
          '<p class="empty__text">' + esc(t('emptyText')) + '</p>' +
        '</div>';
      $('#receiptTotals').hidden = true;
      $('#receiptForm').hidden = true;
      $('#receiptFoot').hidden = true;
      return;
    }

    box.innerHTML = cart.map((line) => {
      const unit = lineUnit(line);
      const mods = lineChoices(line).map((m) => L(m.choice.name));

      return '<div class="rline">' +
        '<div class="rline__top">' +
          '<span class="rline__name">' + esc(L(lineItem(line).name)) + '</span>' +
          '<span class="rline__dots"></span>' +
          '<span class="rline__sum">' + money(unit * line.qty) + '</span>' +
        '</div>' +
        (mods.length ? '<p class="rline__mods">' + esc(mods.join(' · ')) + '</p>' : '') +
        '<div class="rline__ctrl">' +
          '<span class="rline__unit">' + line.qty + ' × ' + money(unit) + '</span>' +
          '<div class="rstep">' +
            '<button type="button" data-line="' + esc(line.key) + '" data-d="-1" aria-label="' + esc(t('decAria', { name: L(lineItem(line).name) })) + '">' + iconMinus + '</button>' +
            '<span class="rstep__n">' + line.qty + '</span>' +
            '<button type="button" data-line="' + esc(line.key) + '" data-d="1" aria-label="' + esc(t('incAria', { name: L(lineItem(line).name) })) + '">' + iconPlus + '</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');

    const sub = cartSubtotal();
    const dlv = deliveryCost();

    $('#tPositions').textContent = n + ' ' + plural(n, t('positions'));
    $('#tSubtotal').textContent = money(sub);
    $('#tDeliveryRow').hidden = deliveryMode !== 'delivery';
    $('#tDelivery').textContent = dlv ? money(dlv) : t('rFree');
    $('#tGrand').textContent = money(sub + dlv);

    $('#receiptTotals').hidden = false;
    $('#receiptForm').hidden = false;
    $('#receiptFoot').hidden = false;

    updateHint();
    drawBarcode();
  }

  function updateHint() {
    const sub = cartSubtotal();
    const parts = [];

    if (deliveryMode === 'delivery') {
      if (sub < CONFIG.minOrder) {
        parts.push(t('hintMinOrder', { min: money(CONFIG.minOrder), left: money(CONFIG.minOrder - sub) }));
      } else if (sub < CONFIG.freeDeliveryFrom) {
        parts.push(t('hintToFree', { left: money(CONFIG.freeDeliveryFrom - sub) }));
      } else {
        parts.push(t('hintFree'));
      }
      parts.push(t('hintCourier'));
    } else if (deliveryMode === 'pickup') {
      parts.push(t('hintPickup'));
    } else {
      parts.push(t('hintTable'));
    }

    if (!isOpenNow()) parts.push(t('hintClosed'));

    $('#orderHint').textContent = parts.join(' ');
  }

  function setMode(mode) {
    deliveryMode = mode;
    store.set('lazza_mode_v1', mode);

    $$('.seg').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
    $('#fTable').hidden = mode !== 'table';
    $('#fAddress').hidden = mode !== 'delivery';
    $('#fPhone').hidden = mode === 'table';

    $$('.field').forEach((f) => f.classList.remove('is-error'));
    renderReceipt();
  }

  /* ============================================================
     ОТПРАВКА ЗАКАЗА
     ============================================================ */

  function fail(fieldId) {
    const field = $(fieldId);
    field.classList.add('is-error');
    const input = $('input, textarea', field);
    if (input) { input.focus(); input.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
    return false;
  }

  function validateOrder() {
    $$('.field').forEach((f) => f.classList.remove('is-error'));

    if (!$('#iName').value.trim()) return fail('#fName');
    if (deliveryMode === 'table' && !String($('#iTable').value).trim()) return fail('#fTable');

    if (deliveryMode === 'delivery') {
      if ($('#iAddress').value.trim().length < 6) return fail('#fAddress');
      if ($('#iPhone').value.replace(/\D/g, '').length < 9) return fail('#fPhone');
      if (cartSubtotal() < CONFIG.minOrder) {
        toast(t('tMinOrder', { min: money(CONFIG.minOrder) }));
        return false;
      }
    }
    return true;
  }

  function orderText() {
    const sub = cartSubtotal();
    const dlv = deliveryCost();
    const lines = [];

    lines.push('*' + t('mOrder') + ' · ' + CONFIG.name.toUpperCase() + '*');
    lines.push('№ ' + orderNo + ' · ' + stamp(false));
    lines.push('');

    cart.forEach((line, i) => {
      const unit = lineUnit(line);
      lines.push((i + 1) + '. ' + L(lineItem(line).name) + ' × ' + line.qty + ' — ' + money(unit * line.qty));
      const mods = lineChoices(line).map((m) => L(m.choice.name));
      if (mods.length) lines.push('    ' + mods.join(', '));
    });

    lines.push('');
    lines.push(t('mSum') + ': ' + money(sub));
    if (deliveryMode === 'delivery') lines.push(t('mDelivery') + ': ' + (dlv ? money(dlv) : t('rFree')));
    lines.push('*' + t('mTotal') + ': ' + money(sub + dlv) + '*');
    lines.push('');

    const modeName = { table: t('segTable'), pickup: t('segPickup'), delivery: t('segDelivery') }[deliveryMode];
    lines.push(t('mWay') + ': ' + modeName);

    const cafeAddr = L(CONFIG.address) + ', ' + L(CONFIG.city);

    if (deliveryMode === 'table') {
      lines.push(t('mTable') + ': № ' + $('#iTable').value.trim());
      lines.push(t('mCafe') + ': ' + cafeAddr);
    }
    if (deliveryMode === 'pickup') lines.push(t('mPickup') + ': ' + cafeAddr);
    if (deliveryMode === 'delivery') lines.push(t('mAddress') + ': ' + $('#iAddress').value.trim());

    lines.push(t('mName') + ': ' + $('#iName').value.trim());

    const phone = $('#iPhone').value.trim();
    if (phone && deliveryMode !== 'table') lines.push(t('mPhone') + ': ' + phone);

    const note = $('#iNote').value.trim();
    if (note) lines.push(t('mNote') + ': ' + note.slice(0, 400));

    return lines.join('\n');
  }

  function sendOrder() {
    if (!cart.length || !validateOrder()) return;

    if (CONFIG.whatsapp === '994501234567') toast(t('tDemo'));

    window.open('https://wa.me/' + CONFIG.whatsapp + '?text=' + encodeURIComponent(orderText()), '_blank', 'noopener');

    cart = [];
    saveCart();
    updateBar();
    refreshAllCards();
    renderReceipt();
    closeSheet();

    orderNo = 'A-' + String(Math.floor(Math.random() * 9000) + 1000);
    try { sessionStorage.setItem('lazza_order_no', orderNo); } catch (e) { /* ignore */ }
    $('#receiptNo').textContent = '№ ' + orderNo;

    setTimeout(() => toast(t('tOrderSent')), 400);
  }

  /* ============================================================
     ОТЗЫВЫ
     ============================================================ */

  const starsHTML = (rating) => Array.from({ length: 5 }, (_, i) => (
    '<svg' + (i < rating ? '' : ' class="is-off"') + ' aria-hidden="true"><use href="#i-star"/></svg>'
  )).join('');

  const allReviews = () => reviews.concat(SEED_REVIEWS);

  function renderReviews() {
    const list = allReviews();
    const avg = list.reduce((s, r) => s + r.rating, 0) / list.length;

    $('#ratingScore').textContent = num(avg, 1);
    $('#ratingStars').innerHTML = starsHTML(Math.round(avg));
    $('#ratingMeta').textContent = t('basedOn', { n: list.length });

    $('#reviewList').innerHTML = list.map((r) => {
      const mine = reviews.indexOf(r) > -1;

      return '<article class="review' + (mine ? ' review--mine' : '') + '">' +
        '<div class="review__top">' +
          '<span class="review__avatar">' + esc(r.name.slice(0, 1).toUpperCase()) + '</span>' +
          '<span class="review__who">' +
            '<span class="review__name">' + esc(r.name) + '</span>' +
            (mine ? '<span class="review__tag">' + esc(t('yourReview')) + '</span>' : '') +
            '<br><span class="review__date">' + esc(dateText(r.date)) + '</span>' +
          '</span>' +
          '<span class="stars">' + starsHTML(r.rating) + '</span>' +
        '</div>' +
        '<p class="review__text">' + esc(L(r.text)) + '</p>' +
      '</article>';
    }).join('');
  }

  let reviewRating = 5;

  function renderStarPick() {
    $('#starPick').innerHTML = Array.from({ length: 5 }, (_, i) => (
      '<button type="button" data-star="' + (i + 1) + '"' +
        (i < reviewRating ? ' class="is-on"' : '') +
        ' aria-label="' + esc(t('ratingAria', { n: i + 1 })) + '"' +
        ' aria-pressed="' + (i + 1 === reviewRating) + '">' +
        '<svg aria-hidden="true"><use href="#i-star"/></svg></button>'
    )).join('');
  }

  function sendReview() {
    $$('.field').forEach((f) => f.classList.remove('is-error'));

    const name = $('#iRName').value.trim();
    const text = $('#iRText').value.trim();

    if (!name) return fail('#fRName');
    if (text.length < 5) return fail('#fRText');

    /* отзыв гостя написан на одном языке — показываем его как есть */
    reviews.unshift({
      name: name,
      rating: reviewRating,
      text: { az: text, ru: text, en: text },
      date: new Date().toISOString().slice(0, 10),
    });
    store.set('lazza_reviews_v1', reviews);
    renderReviews();

    const msg = '*' + t('mReview') + ' · ' + CONFIG.name.toUpperCase() + '*\n' +
      t('mRating') + ': ' + '★'.repeat(reviewRating) + '☆'.repeat(5 - reviewRating) +
      ' (' + t('mOf', { n: reviewRating }) + ')\n' +
      t('mName') + ': ' + name + '\n\n' + text;

    window.open('https://wa.me/' + CONFIG.whatsapp + '?text=' + encodeURIComponent(msg), '_blank', 'noopener');

    $('#iRName').value = '';
    $('#iRText').value = '';
    reviewRating = 5;
    renderStarPick();
    closeSheet();
    setTimeout(() => toast(t('tReviewSent')), 400);
  }

  /* ============================================================
     ЛИСТЫ, ТОСТ, НАВИГАЦИЯ
     ============================================================ */

  let activeSheet = null;
  let lastFocused = null;

  function openSheet(sheet) {
    if (activeSheet) closeSheet(true);

    activeSheet = sheet;
    lastFocused = document.activeElement;

    sheet.hidden = false;
    document.body.classList.add('is-locked');
    $('#scrim').classList.add('is-open');

    requestAnimationFrame(() => requestAnimationFrame(() => {
      sheet.classList.add('is-open');
      const focusable = $('button:not([disabled]), input, textarea', sheet);
      if (focusable) focusable.focus({ preventScroll: true });
    }));
  }

  function closeSheet(instant) {
    if (!activeSheet) return;
    const sheet = activeSheet;
    activeSheet = null;
    if (sheet.id === 'detailSheet') {
      draft = null;
      if (window.LazzaAR) window.LazzaAR.reset();
    }

    sheet.classList.remove('is-open');
    $('#scrim').classList.remove('is-open');
    document.body.classList.remove('is-locked');

    const finish = () => {
      sheet.hidden = true;
      const scroller = $('.sheet__scroll', sheet);
      if (scroller) scroller.scrollTop = 0;
    };

    if (instant) finish();
    else setTimeout(finish, 420);

    if (lastFocused && lastFocused.focus) lastFocused.focus({ preventScroll: true });
  }

  let toastTimer = null;

  function toast(text) {
    const el = $('#toast');
    el.textContent = text;
    el.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('is-on'), 2400);
  }

  let spy = null;

  /* двигаем только горизонтальную ленту категорий, страницу не трогаем */
  function centerNavBtn(btn) {
    const box = $('#navScroll');
    const left = btn.offsetLeft - (box.clientWidth - btn.offsetWidth) / 2;
    box.scrollTo({ left: Math.max(0, left), behavior: 'smooth' });
  }

  function markNav(id) {
    $$('.nav__btn').forEach((b) => {
      const on = b.dataset.goto === id;
      b.setAttribute('aria-current', String(on));
      if (on) centerNavBtn(b);
    });
  }

  /* Плавно — только на близкое расстояние. Через всю страницу анимация тянется
     секундами, гость решает, что нажатие не сработало, и жмёт ещё раз. */
  function goToSection(id) {
    const target = document.getElementById(id);
    if (!target) return;

    markNav(id);

    const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY -
      ($('.nav').offsetHeight + 6));
    const far = Math.abs(top - window.scrollY) > window.innerHeight * 1.2;
    const smooth = !far && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    window.scrollTo({ top: top, behavior: smooth ? 'smooth' : 'auto' });
  }

  function setupScrollSpy() {
    if (spy) spy.disconnect();

    const buttons = $$('.nav__btn');
    const sections = buttons.map((b) => document.getElementById(b.dataset.goto));

    spy = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) markNav(entry.target.id);
      });
    }, { rootMargin: '-58px 0px -72% 0px', threshold: 0 });

    sections.forEach((s) => s && spy.observe(s));
  }

  /* ============================================================
     СОБЫТИЯ
     ============================================================ */

  function bind() {
    document.addEventListener('click', (e) => {
      const langBtn = e.target.closest('[data-lang]');
      if (langBtn) { setLang(langBtn.dataset.lang); return; }
      if (e.target.closest('.skin')) toggleSkin();
    });

    $('#menuRoot').addEventListener('click', (e) => {
      const open = e.target.closest('.card__open');
      if (open) return openDetail(open.dataset.id);

      const add = e.target.closest('[data-act="add"]');
      if (add) {
        const item = ITEMS[add.dataset.id];
        if (item.mods && item.mods.length) openDetail(item.id);
        else quickAdd(item, 1);
        return;
      }

      const step = e.target.closest('[data-act="inc"], [data-act="dec"]');
      if (step) {
        const id = step.closest('.stepper').dataset.id;
        quickAdd(ITEMS[id], step.dataset.act === 'inc' ? 1 : -1);
      }
    });

    $('#navScroll').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-goto]');
      if (btn) goToSection(btn.dataset.goto);
    });

    $('.hero__scroll').addEventListener('click', (e) => {
      e.preventDefault();
      goToSection('burgers');
    });

    $('#detailMods').addEventListener('change', (e) => {
      const input = e.target;
      if (!input.dataset.group) return;
      const gi = Number(input.dataset.group);
      const ci = Number(input.value);

      if (input.type === 'radio') {
        draft.picked[gi] = [ci];
      } else {
        const set = new Set(draft.picked[gi] || []);
        if (input.checked) set.add(ci); else set.delete(ci);
        draft.picked[gi] = Array.from(set);
      }
      updateDetailSum();
    });

    $('#qtyPlus').addEventListener('click', () => {
      draft.qty = Math.min(draft.qty + 1, 30);
      $('#qtyN').textContent = draft.qty;
      $('#qtyMinus').disabled = draft.qty <= 1;
      updateDetailSum();
    });

    $('#qtyMinus').addEventListener('click', () => {
      draft.qty = Math.max(1, draft.qty - 1);
      $('#qtyN').textContent = draft.qty;
      $('#qtyMinus').disabled = draft.qty <= 1;
      updateDetailSum();
    });

    $('#detailAdd').addEventListener('click', () => {
      addToCart(draft.item, selectedMods(), draft.qty);
      closeSheet();
    });

    $('#cartBtn').addEventListener('click', () => {
      renderReceipt();
      setMode(deliveryMode);
      if (tableNo && !$('#iTable').value) $('#iTable').value = tableNo;
      openSheet($('#cartSheet'));
    });

    $('#receiptItems').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-line]');
      if (btn) changeLine(btn.dataset.line, Number(btn.dataset.d));
    });

    $('#receiptForm').addEventListener('click', (e) => {
      const seg = e.target.closest('.seg');
      if (seg) setMode(seg.dataset.mode);
    });

    $('#sendOrder').addEventListener('click', sendOrder);

    $('#openReview').addEventListener('click', () => {
      renderStarPick();
      openSheet($('#reviewSheet'));
    });

    $('#starPick').addEventListener('click', (e) => {
      const star = e.target.closest('[data-star]');
      if (!star) return;
      reviewRating = Number(star.dataset.star);
      renderStarPick();
    });

    $('#sendReview').addEventListener('click', sendReview);

    $('#scrim').addEventListener('click', () => closeSheet());
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-close]')) closeSheet();
    });

    document.addEventListener('keydown', (e) => {
      if (!activeSheet) return;
      if (e.key === 'Escape') { closeSheet(); return; }

      if (e.key === 'Tab') {
        const items = $$('button:not([disabled]), input:not([type="radio"]):not([type="checkbox"]), textarea, [href]', activeSheet)
          .filter((el) => el.offsetParent !== null);
        if (!items.length) return;

        const first = items[0];
        const last = items[items.length - 1];

        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }

  /* ============================================================
     СТАРТ
     ============================================================ */

  if (tableNo) {
    deliveryMode = 'table';
    store.set('lazza_mode_v1', 'table');
  }

  applySkin();
  window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
    if (skinPref === 'auto') applySkin();
  });

  renderLangs();
  renderStatics();
  renderMenu();
  renderReviews();
  renderStarPick();
  bind();
  setupScrollSpy();
  updateBar();
  renderReceipt();
})();
