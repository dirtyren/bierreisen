(function () {
  var raw = document.getElementById('i18n-catalog');
  if (!raw) return;
  var MAP = JSON.parse(raw.textContent);
  var KEY = 'bierreisen:lang';
  var TITLE_EN = document.title;
  var textOrig = new WeakMap();
  var blockOrig = new WeakMap();
  var attrOrig = new WeakMap();
  var busy = false;
  var WORD = /[\p{L}\p{N}]/u;

  function norm(s) { return s.replace(/\s+/g, ' ').replace(/\s+([,.;:!?)\]])(?=\s|$)/g, '$1').replace(/\(\s+/g, '(').trim(); }
  function pick(lang) { return lang === 'pt-BR' ? 'pt' : lang; }

  /* Split "📋 Itinerary" into ["📋 ", "Itinerary", ""] so the emoji survives translation. */
  function affixSplit(s) {
    var i = 0, j = s.length;
    while (i < j && !WORD.test(s[i])) i++;
    while (j > i && !WORD.test(s[j - 1])) j--;
    return [s.slice(0, i), s.slice(i, j), s.slice(j)];
  }

  function translateString(text, lang) {
    if (!text) return null;
    var lead = text.match(/^\s*/)[0];
    var trail = text.match(/\s*$/)[0];
    var body = text.slice(lead.length, text.length - trail.length);
    var entry = MAP[norm(body)];
    var parts = entry ? null : affixSplit(body);
    if (!entry && parts) entry = MAP[norm(parts[1])];
    if (!entry) return null;
    var val = entry[pick(lang)];
    if (!val) return null;
    if (parts) return lead + parts[0] + val + parts[2] + trail;
    return lead + val + trail;
  }

  function tx(node, lang) {
    if (!node || node.nodeType !== 3) return false;
    var parent = node.parentNode;
    if (parent && /^(SCRIPT|STYLE)$/.test(parent.nodeName)) return false;
    if (parent && parent.closest && parent.closest('.lang-switch')) return false;
    var cur = node.nodeValue;
    if (!cur || !WORD.test(cur)) return false;
    if (!textOrig.has(node)) textOrig.set(node, cur);
    var base = textOrig.get(node);
    if (lang === 'en') { if (node.nodeValue !== base) { node.nodeValue = base; return true; } return false; }
    var out = translateString(base, lang);
    if (out === null) return false;
    if (node.nodeValue !== out) { node.nodeValue = out; return true; }
    return false;
  }

  function walkText(root, lang) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n, hits = 0, total = 0;
    while ((n = w.nextNode())) { total++; if (tx(n, lang)) hits++; }
    return { hits: hits, total: total };
  }

  function walkAttrs(root, lang) {
    var attrs = ['title', 'placeholder', 'aria-label', 'alt'];
    var els = root.querySelectorAll('[title],[placeholder],[aria-label],[alt]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var store = attrOrig.get(el) || {};
      for (var a = 0; a < attrs.length; a++) {
        var name = attrs[a];
        if (!el.hasAttribute(name)) continue;
        if (!(name in store)) store[name] = el.getAttribute(name);
        var base = store[name];
        var out = lang === 'en' ? base : translateString(base, lang);
        var want = out === null ? base : out;
        if (el.getAttribute(name) !== want) el.setAttribute(name, want);
      }
      attrOrig.set(el, store);
    }
  }

  /* Text split by inline markup (a route string with <strong>, a base chip with <strong>)
     cannot be matched node by node; match the element and rebuild it as plain text. */
  var INLINE = /^(STRONG|EM|B|I|SPAN|BR|SMALL|U|MARK)$/;
  function inlineOnly(el) {
    for (var c = el.firstElementChild; c; c = c.nextElementSibling) {
      if (!INLINE.test(c.nodeName)) return false;
    }
    return true;
  }

  /* Only leaf-ish text containers: a whole card must never be flattened into one string. */
  function walkBlocks(root, lang) {
    var els = root.querySelectorAll('p,h1,h2,h3,h4,li,td,th,span,label,figcaption,summary,div');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.closest('.lang-switch')) continue;
      if (el.querySelector('a,button,script,style,img,svg,input,select')) continue;
      if (!inlineOnly(el)) continue;
      if (!el.firstChild) continue;
      if (!blockOrig.has(el)) blockOrig.set(el, norm(el.textContent));
      var base = blockOrig.get(el);
      if (lang === 'en') {
        if (norm(el.textContent) !== base) el.textContent = base;
        continue;
      }
      var out = translateString(base, lang);
      if (out !== null && norm(el.textContent) !== out) el.textContent = out;
    }
  }

  function apply(lang) {
    if (busy) return;
    busy = true;
    document.documentElement.lang = lang;
    var stats = walkText(document.body, lang);
    walkAttrs(document.body, lang);
    walkBlocks(document.body, lang);
    if (TITLE_EN) {
      var t = lang === 'en' ? null : translateString(TITLE_EN, lang);
      document.title = t === null ? TITLE_EN : t;
    }
    var chips = document.querySelectorAll('.lang-switch button');
    for (var i = 0; i < chips.length; i++) chips[i].classList.toggle('active', chips[i].dataset.lang === lang);
    window.__i18nStats = { lang: lang, hits: stats.hits, total: stats.total };
    busy = false;
  }

  var stored = 'en';
  try { stored = localStorage.getItem(KEY) || 'en'; } catch (e) {}
  var chips = document.querySelectorAll('.lang-switch button');
  for (var i = 0; i < chips.length; i++) {
    chips[i].addEventListener('click', function () {
      var lang = this.dataset.lang;
      try { localStorage.setItem(KEY, lang); } catch (e) {}
      apply(lang);
    });
  }

  /* Leaflet popups are built after load: translate whatever appears. */
  var mo = new MutationObserver(function (muts) {
    var lang = document.documentElement.lang || 'en';
    if (lang === 'en' || busy) return;
    for (var m = 0; m < muts.length; m++) {
      for (var k = 0; k < muts[m].addedNodes.length; k++) {
        var n = muts[m].addedNodes[k];
        if (n.nodeType === 1) { walkText(n, lang); walkBlocks(n, lang); }
      }
    }
  });
  mo.observe(document.body, { childList: true, subtree: true });

  apply(stored);
  window.__setLang = apply;
})();
