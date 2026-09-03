/* ============================================================
   LAZZA — 3D и дополненная реальность

   Что делает: в карточке блюда показывает кнопку «Смотреть в 3D».
   По нажатию фото сменяется вращающейся 3D-моделью, а на телефоне
   появляется вторая кнопка — «Поставить на стол»: открывается камера
   и блюдо стоит на реальном столе в натуральную величину.

   Работает без установки приложений:
     Android — Google Scene Viewer, iPhone/iPad — AR Quick Look.
   Требуется https (у нас есть) и модель .glb у позиции меню (menu.js).

   Движок — model-viewer от Google, лежит локально в vendor/.
   Грузится только когда гость сам нажал «Смотреть в 3D».
   ============================================================ */

(function () {
  'use strict';

  var LIB = 'vendor/model-viewer.min.js';
  var LIB_TIMEOUT = 12000;

  var stage, toggle, toggleText, photo;
  var viewer = null;
  var current = null;   /* позиция, для которой сейчас открыт 3D */
  var shown = false;
  var T = function (key) { return key; };

  function loadLib() {
    if (loadLib.promise) return loadLib.promise;

    loadLib.promise = new Promise(function (resolve, reject) {
      var done = false;
      var fail = function () { if (!done) { done = true; reject(new Error('model-viewer')); } };
      var ok = function () { if (!done) { done = true; resolve(); } };

      var tag = document.createElement('script');
      tag.type = 'module';
      tag.src = LIB;
      tag.onerror = fail;
      tag.onload = function () {
        if (window.customElements) customElements.whenDefined('model-viewer').then(ok, fail);
        else fail();
      };
      document.head.appendChild(tag);
      setTimeout(fail, LIB_TIMEOUT);   /* браузер без модулей не должен вешать кнопку */
    });

    return loadLib.promise;
  }

  var noteTimer = null;

  /* Подсказка поверх сцены. ttl — через сколько убрать,
     чтобы текст не закрывал высокие блюда (стакан с трубочкой). */
  function note(text, opts) {
    opts = opts || {};
    var el = stage.querySelector('.ar__note');
    if (!el) {
      el = document.createElement('p');
      el.className = 'ar__note';
      stage.appendChild(el);
    }

    clearTimeout(noteTimer);
    el.textContent = text || '';
    el.hidden = !text;
    el.classList.toggle('ar__note--warn', opts.kind === 'warn');
    el.classList.remove('ar__note--fade');

    if (text && opts.ttl) {
      noteTimer = setTimeout(function () {
        el.classList.add('ar__note--fade');
        noteTimer = setTimeout(function () { el.hidden = true; }, 400);
      }, opts.ttl);
    }
  }

  function hintFor(mv) {
    note(mv.canActivateAR ? T('arDrag') : T('arPhone'), { ttl: 4500 });
  }

  function build(item) {
    var mv = document.createElement('model-viewer');

    mv.setAttribute('src', item.model);
    mv.setAttribute('poster', item.img);
    mv.setAttribute('alt', item.alt || '');

    /* просмотр */
    mv.setAttribute('camera-controls', '');
    mv.setAttribute('touch-action', 'pan-y');       /* лист блюда остаётся прокручиваемым */
    mv.setAttribute('auto-rotate', '');
    mv.setAttribute('auto-rotate-delay', '400');
    mv.setAttribute('rotation-per-second', '22deg');
    mv.setAttribute('interaction-prompt', 'none');
    mv.setAttribute('camera-orbit', '25deg 72deg 118%');
    mv.setAttribute('min-camera-orbit', 'auto 15deg auto');
    mv.setAttribute('max-camera-orbit', 'auto 95deg auto');
    mv.setAttribute('shadow-intensity', '1.4');
    mv.setAttribute('shadow-softness', '0.85');
    mv.setAttribute('exposure', '0.82');
    mv.setAttribute('tone-mapping', 'commerce');

    /* дополненная реальность */
    mv.setAttribute('ar', '');
    mv.setAttribute('ar-modes', 'webxr scene-viewer quick-look');
    mv.setAttribute('ar-scale', 'fixed');           /* натуральный размер порции */
    mv.setAttribute('ar-placement', 'floor');

    var place = document.createElement('button');
    place.type = 'button';
    place.className = 'ar__place';
    place.setAttribute('slot', 'ar-button');
    place.innerHTML = '<svg aria-hidden="true"><use href="#i-ar"/></svg><span></span>';
    place.querySelector('span').textContent = T('arPlace');
    place.hidden = true;
    mv.appendChild(place);

    mv.addEventListener('load', function () {
      hintFor(mv);
      place.hidden = !mv.canActivateAR;
    });

    mv.addEventListener('error', function () {
      note(T('arFail'), { kind: 'warn' });
      showPhoto();
    });

    return mv;
  }

  function showPhoto() {
    shown = false;
    stage.hidden = true;
    photo.hidden = false;
    if (viewer) { viewer.remove(); viewer = null; }
    note('');
    label();
  }

  function show3d(item) {
    shown = true;
    photo.hidden = true;
    stage.hidden = false;
    note(T('arLoading'));
    label();

    toggle.disabled = true;
    loadLib().then(function () {
      toggle.disabled = false;
      if (!shown || current !== item) return;      /* гость успел передумать */
      viewer = build(item);
      stage.insertBefore(viewer, stage.firstChild);
    }, function () {
      toggle.disabled = false;
      note(T('arFail'), { kind: 'warn' });
      setTimeout(showPhoto, 1600);
    });
  }

  function label() {
    toggleText.textContent = shown ? T('arPhoto') : T('ar3d');
    toggle.classList.toggle('ar-toggle--on', shown);
  }

  function init() {
    stage = document.getElementById('arStage');
    toggle = document.getElementById('arToggle');
    toggleText = document.getElementById('arToggleText');
    photo = document.getElementById('detailImg');
    if (!stage || !toggle) return;

    toggle.addEventListener('click', function () {
      if (!current) return;
      if (shown) showPhoto();
      else show3d(current);
    });
  }

  /* ------------------------------------------------------------
     Что вызывает app.js
     ------------------------------------------------------------ */

  window.LazzaAR = {
    /* открылась карточка блюда (или сменился язык) */
    sync: function (item, t) {
      if (!stage) init();
      if (!stage) return;

      T = t || T;
      var has = !!(item && item.model);
      toggle.hidden = !has;

      if (!has || !current || current.id !== item.id) showPhoto();
      current = has ? item : null;

      if (has && shown && viewer) {
        var place = viewer.querySelector('.ar__place span');
        if (place) place.textContent = T('arPlace');
        hintFor(viewer);
      }
      label();
    },

    /* карточка закрылась — освобождаем видеопамять */
    reset: function () {
      if (!stage) return;
      current = null;
      showPhoto();
    },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
