/* ============================================================
   LAZZA — 3D и камера

   В карточке блюда есть кнопка «Смотреть в 3D»: фото сменяется
   моделью, которую крутят пальцем.

   Дальше — «Поставить на стол». Здесь два режима, и это важно:

   1. БЫСТРЫЙ (по умолчанию). Включаем камеру телефона и рисуем
      блюдо поверх картинки. Открывается сразу — ждать нечего.
      Блюдо не привязано к столу: гость сам наводит его пальцем,
      двумя пальцами меняет размер.

   2. ТОЧНЫЙ — кнопка «Закрепить на столе» уже внутри камеры.
      Это настоящий AR: Google Scene Viewer на Android и AR Quick
      Look на iPhone. Блюдо прилипает к столу и остаётся на месте,
      когда обходишь его вокруг. Цена — несколько секунд: система
      просит поводить камерой, пока не найдёт плоскость. Убрать это
      ожидание нельзя, оно внутри ARCore и ARKit.

   Требуется https (у нас есть) и модель .glb у позиции (menu.js).
   Движок — model-viewer от Google, лежит локально в vendor/,
   грузится только когда гость сам нажал «Смотреть в 3D».
   ============================================================ */

(function () {
  'use strict';

  var LIB = 'vendor/model-viewer.min.js';
  var LIB_TIMEOUT = 12000;

  var stage, toggle, toggleText, photo, place;
  var viewer = null;
  var cam = null;       /* открытый экран камеры */
  var current = null;   /* позиция, для которой сейчас открыт 3D */
  var shown = false;
  var noteTimer = null;
  var T = function (key) { return key; };

  function el(tag, cls) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    return node;
  }

  /* ------------------------------------------------------------
     Движок
     ------------------------------------------------------------ */

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

  /* Умеет ли телефон показать камеру прямо в странице */
  function canCamera() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia) &&
      window.matchMedia('(pointer: coarse)').matches;
  }

  /* ------------------------------------------------------------
     Подсказка поверх сцены
     ------------------------------------------------------------ */

  /* ttl — через сколько убрать, чтобы текст не закрывал высокие
     блюда вроде стакана с трубочкой */
  function note(text, opts) {
    opts = opts || {};
    var node = stage.querySelector('.ar__note');
    if (!node) {
      node = el('p', 'ar__note');
      stage.appendChild(node);
    }

    clearTimeout(noteTimer);
    node.textContent = text || '';
    node.hidden = !text;
    node.classList.toggle('ar__note--warn', opts.kind === 'warn');
    node.classList.remove('ar__note--fade');

    if (text && opts.ttl) {
      noteTimer = setTimeout(function () {
        node.classList.add('ar__note--fade');
        noteTimer = setTimeout(function () { node.hidden = true; }, 400);
      }, opts.ttl);
    }
  }

  /* ------------------------------------------------------------
     Модель
     ------------------------------------------------------------ */

  function buildViewer(item, live) {
    var mv = document.createElement('model-viewer');

    mv.setAttribute('src', item.model);
    mv.setAttribute('alt', '');
    mv.setAttribute('camera-controls', '');
    mv.setAttribute('interaction-prompt', 'none');
    mv.setAttribute('shadow-softness', '0.85');
    mv.setAttribute('tone-mapping', 'commerce');

    /* настоящий AR — доступен в обоих режимах */
    mv.setAttribute('ar', '');
    mv.setAttribute('ar-modes', 'webxr scene-viewer quick-look');
    mv.setAttribute('ar-scale', 'fixed');       /* натуральный размер порции */
    mv.setAttribute('ar-placement', 'floor');

    if (live) {
      /* поверх камеры: блюдо примерно натуральной величины,
         как будто смотришь на стол с расстояния вытянутой руки */
      mv.className = 'arcam__model';
      /* Расстояние и угол обзора заданы вручную и сняты с автоподбора
         (min/max), иначе model-viewer сам вписывает модель в кадр и
         масштаб перестаёт быть похожим на настоящий. */
      mv.setAttribute('camera-orbit', '0deg 68deg 0.45m');
      mv.setAttribute('min-camera-orbit', 'auto 0deg 0.10m');
      mv.setAttribute('max-camera-orbit', 'auto 100deg 3m');
      mv.setAttribute('field-of-view', '58deg');
      mv.setAttribute('min-field-of-view', '12deg');
      mv.setAttribute('max-field-of-view', '85deg');
      mv.setAttribute('shadow-intensity', '0.9');
      mv.setAttribute('exposure', '1');
    } else {
      mv.setAttribute('poster', item.img);
      mv.setAttribute('touch-action', 'pan-y');   /* лист блюда остаётся прокручиваемым */
      mv.setAttribute('auto-rotate', '');
      mv.setAttribute('auto-rotate-delay', '400');
      mv.setAttribute('rotation-per-second', '22deg');
      mv.setAttribute('camera-orbit', '25deg 72deg 118%');
      mv.setAttribute('min-camera-orbit', 'auto 15deg auto');
      mv.setAttribute('max-camera-orbit', 'auto 95deg auto');
      mv.setAttribute('shadow-intensity', '1.4');
      mv.setAttribute('exposure', '0.82');
    }

    return mv;
  }

  /* ------------------------------------------------------------
     Экран камеры — открывается мгновенно
     ------------------------------------------------------------ */

  function closeCamera() {
    if (!cam) return;
    if (cam.stream) cam.stream.getTracks().forEach(function (track) { track.stop(); });
    document.removeEventListener('keydown', cam.onKey);
    cam.root.remove();
    cam = null;
  }

  function openCamera(item) {
    if (cam) return;

    var root = el('div', 'arcam');

    var video = el('video', 'arcam__video');
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    video.setAttribute('playsinline', '');      /* iOS: иначе видео уходит в полный экран */

    var mv = buildViewer(item, true);

    var close = el('button', 'arcam__close');
    close.type = 'button';
    close.setAttribute('aria-label', T('arCamClose'));
    close.innerHTML = '<svg aria-hidden="true"><use href="#i-close"/></svg>';

    var hint = el('p', 'arcam__hint');
    hint.textContent = T('arPinch');

    /* «Закрепить на столе» — настоящий AR. Слот ar-button означает,
       что нажатие само запускает Scene Viewer или Quick Look. */
    var anchor = el('button', 'arcam__anchor');
    anchor.type = 'button';
    anchor.setAttribute('slot', 'ar-button');
    anchor.innerHTML = '<svg aria-hidden="true"><use href="#i-ar"/></svg><span></span>';
    anchor.querySelector('span').textContent = T('arAnchor');
    anchor.hidden = true;
    mv.appendChild(anchor);

    mv.addEventListener('load', function () {
      anchor.hidden = !mv.canActivateAR;
      /* при загрузке модели model-viewer сам вписывает её в кадр
         и сбрасывает угол обзора — возвращаем свой, «телефонный» */
      mv.fieldOfView = '58deg';
      mv.cameraOrbit = '0deg 68deg 0.45m';
    });

    var onKey = function (e) { if (e.key === 'Escape') closeCamera(); };
    close.addEventListener('click', closeCamera);
    document.addEventListener('keydown', onKey);

    root.appendChild(video);
    root.appendChild(mv);
    root.appendChild(close);
    root.appendChild(hint);
    document.body.appendChild(root);

    cam = { root: root, video: video, mv: mv, stream: null, onKey: onKey };

    navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    }).then(function (stream) {
      if (!cam) {                                /* успели закрыть */
        stream.getTracks().forEach(function (t) { t.stop(); });
        return;
      }
      cam.stream = stream;
      video.srcObject = stream;
      var playing = video.play();
      if (playing && playing.catch) playing.catch(function () {});
      setTimeout(function () {
        if (cam) hint.classList.add('arcam__hint--fade');
      }, 5000);
    }, function () {
      /* камеру не дали — остаёмся на тёмном фоне и объясняем почему */
      if (!cam) return;
      hint.textContent = T('arCamDenied');
      hint.classList.add('arcam__hint--warn');
    });
  }

  /* ------------------------------------------------------------
     Фото ↔ 3D в карточке блюда
     ------------------------------------------------------------ */

  function showPhoto() {
    shown = false;
    closeCamera();
    stage.hidden = true;
    photo.hidden = false;
    if (viewer) { viewer.remove(); viewer = null; }
    place.hidden = true;
    note('');
    label();
  }

  /* модель загрузилась — решаем, показывать ли «Поставить на стол» */
  function readyState(mv) {
    var ok = canCamera() || mv.canActivateAR;
    place.querySelector('span').textContent = T('arPlace');
    place.hidden = !ok;
    note(ok ? T('arDrag') : T('arPhone'), { ttl: 4500 });
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
      viewer = buildViewer(item, false);
      viewer.addEventListener('load', function () { readyState(viewer); });
      viewer.addEventListener('error', function () {
        note(T('arFail'), { kind: 'warn' });
        showPhoto();
      });
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

    /* «Поставить на стол» стоит рядом с моделью, а не в слоте
       ar-button: слот запускал бы медленный AR сразу, а нам нужна
       быстрая камера. Настоящий AR — уже внутри неё. */
    place = el('button', 'ar__place');
    place.type = 'button';
    place.innerHTML = '<svg aria-hidden="true"><use href="#i-ar"/></svg><span></span>';
    place.hidden = true;
    stage.appendChild(place);

    place.addEventListener('click', function () {
      if (!current) return;
      if (canCamera()) openCamera(current);
      else if (viewer && viewer.canActivateAR) viewer.activateAR();
    });

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

      if (has && shown && viewer) readyState(viewer);
      label();
    },

    /* карточка закрылась — гасим камеру и освобождаем видеопамять */
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
