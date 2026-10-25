const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../templates/index.html'), 'utf8');
test('video links with signed query strings and fragments use the video path', () => {
  const context = vm.createContext({});
  const definition = html.match(/function mediaTypeOf\(u\)\{[\s\S]*?\n\}/)[0];
  vm.runInContext(definition, context);
  for (const url of ['https://cdn.example/file.mp4?token=x', 'https://cdn.example/file.WEBM#fragment', 'https://cdn.example/file.m4v']) {
    assert.equal(context.mediaTypeOf(url), 'video');
  }
  assert.equal(context.mediaTypeOf('https://cdn.example/file.jpg?name=video.mp4'), 'image');
  assert.ok(html.includes('/api/proxy-video?url='));
});
const start = html.indexOf('function esc(');
const end = html.indexOf('// END SECURITY HELPERS');
assert.ok(start >= 0 && end > start);
function helpers(extra = {}) {
  const context = vm.createContext({URL, AVAL_LABEL: {}, ...extra});
  vm.runInContext(html.match(/function mediaTypeOf\(u\)\{[\s\S]*?\n\}/)[0], context);
  vm.runInContext(html.slice(start, end), context);
  return context;
}

test('every inline script and standalone viewer script parses', () => {
  for (const script of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)) {
    new vm.Script(script[1]);
  }
  for (const file of ['viewer.js', 'i18n.js']) {
    new vm.Script(fs.readFileSync(path.join(__dirname, '../templates', file), 'utf8'));
  }
});

test('artist payload is data, never executable inline JavaScript', () => {
  const h = helpers();
  const artist = "'-probe()-'\"><img src=x onerror=probe()>";
  const badge = h.artistBadge(artist);
  assert.ok(!badge.includes('onclick='));
  assert.ok(!badge.includes('<img'));
  assert.ok(badge.includes('&quot;'));
  let clicked;
  h.searchArtist = value => { clicked = value; };
  let handler;
  const element = {dataset: {uiAction: 'artist', artist}, closest: () => null,
    addEventListener: (_, fn) => { handler = fn; }};
  h.bindSecurityActions({querySelectorAll: () => [element]});
  handler({stopPropagation() {}});
  assert.equal(clicked, artist);
});

test('only explicit http(s) external links are accepted', () => {
  const h = helpers();
  for (const url of ['javascript:probe()', 'data:text/html,test', '//evil.example', 'file:///c:/secret', '\nJaVaScRiPt:probe()']) {
    assert.equal(h.safeExternalUrl(url), '');
    assert.equal(h.externalLink(url, 'open'), '');
  }
  assert.equal(h.safeExternalUrl('https://example.org/art'), 'https://example.org/art');
  assert.ok(h.externalLink('https://example.org/', 'open').includes('rel="noopener noreferrer"'));
});

test('tag suggestions escape text and attributes', () => {
  const result = helpers().tagSuggestionsHtml([{value: '\"><svg onload=probe()>', post_count: 1}]);
  assert.ok(!result.includes('<svg'));
  assert.ok(result.includes('&lt;svg'));
});

test('gallery uses dataset for ids, filenames and actions', () => {
  const payload = "'-probe()-'\"><script>probe()</script>";
  const result = helpers().galleryCardHtml({
    uid: payload, rel_path: payload, source: payload, artist: payload,
    post_id: payload, page_url: 'javascript:probe()', rating: 'nsfw', _type: 'downloaded',
  }, 0, true);
  assert.ok(!result.includes('<script>'));
  assert.ok(!result.includes('javascript:'));
  assert.ok(result.includes('data-ui-action="delete"'));
  assert.ok(result.includes('data-ui-action="export"'));
  assert.ok(result.includes('nsfw-blur'));
  for (const handler of result.matchAll(/\bon\w+="([^"]*)"/g)) {
    assert.ok(!handler[1].includes('probe'), handler[1]);
    new vm.Script(`(function(event){${handler[1]}})`);
  }
});

test('legacy data interpolation into event handlers does not return', () => {
  for (const old of ["decodeURIComponent('${encodeURIComponent(p.artist)}')", "toggleSelectGroup('${g}'", "deleteGalImage('${relEsc}'", "dupDelete('${relEsc}'"]) {
    assert.ok(!html.includes(old), old);
  }
});

function viewerHarness() {
  function element(uid = '') {
    const classes = new Set();
    return {dataset: {uid}, style: {}, classList: {
      contains: value => classes.has(value),
      add: value => classes.add(value),
      remove: value => classes.delete(value),
      toggle(value, enabled) { if (enabled) classes.add(value); else classes.delete(value); },
    }};
  }
  const cards = [element('source:1'), element('source:2')];
  const elements = {lightbox: element(), lbImg: element(), lbZoomLabel: element(), globalBlurToggle: element()};
  const body = element();
  const context = vm.createContext({window: {}, localStorage: {setItem() {}}, document: {
    body,
    getElementById: id => elements[id],
    addEventListener() {},
    querySelectorAll: selector => selector === '.nsfw-revealed'
      ? [...cards, elements.lightbox].filter(el => el.classList.contains('nsfw-revealed')) : cards,
  }});
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../templates/viewer.js'), 'utf8'), context);
  return {api: context.window, cards, body, ...elements};
}

test('revealed card stays revealed when enlarged; other artwork stays protected', () => {
  const h = viewerHarness();
  h.api.revealNsfwCard({closest: () => h.cards[0]});
  h.api.setLightboxNsfw(true, 'source:1');
  assert.ok(h.lightbox.classList.contains('nsfw-revealed'));
  h.api.lbZoomBy(1);
  assert.ok(h.lightbox.classList.contains('nsfw-revealed'));
  assert.ok(h.lbImg.style.transform.includes('scale(2)'));
  h.api.setLightboxNsfw(true, 'source:2');
  assert.ok(!h.lightbox.classList.contains('nsfw-revealed'));
});

test('revealing the viewer updates only its card; re-enabling blur resets both', () => {
  const h = viewerHarness();
  h.api.setLightboxNsfw(true, 'source:2');
  h.api.revealLightboxNsfw();
  assert.ok(h.cards[1].classList.contains('nsfw-revealed'));
  assert.ok(!h.cards[0].classList.contains('nsfw-revealed'));
  h.api.setNsfwBlur(false);
  assert.ok(h.body.classList.contains('no-nsfw-blur'));
  h.api.setNsfwBlur(true);
  assert.ok(!h.lightbox.classList.contains('nsfw-revealed'));
  assert.ok(!h.cards[1].classList.contains('nsfw-revealed'));
  h.api.setLightboxNsfw(false);
  assert.ok(!h.lightbox.classList.contains('nsfw-blur'));
});

test('hiding from viewer or card synchronizes protection and resets zoom', () => {
  const h = viewerHarness();
  h.api.setLightboxNsfw(true, 'source:1');
  h.api.revealLightboxNsfw();
  h.api.lbZoomBy(1);
  h.api.hideNsfwCard({closest: () => h.cards[0]});
  assert.ok(!h.lightbox.classList.contains('nsfw-revealed'));
  assert.ok(h.lbImg.style.transform.includes('scale(1)'));
  h.api.revealLightboxNsfw();
  h.api.hideLightboxNsfw();
  assert.ok(!h.cards[0].classList.contains('nsfw-revealed'));
  h.api.setNsfwBlur(true);
  h.api.setLightboxNsfw(true, 'source:1');
  assert.ok(!h.lightbox.classList.contains('nsfw-revealed'));
});

test('privacy controls are independent buttons and protected video never autoplays', () => {
  const controls = helpers().artworkPrivacyControls();
  assert.equal((controls.match(/<button/g) || []).length, 2);
  assert.equal((controls.match(/event.stopPropagation/g) || []).length, 2);
  assert.ok(!/<video[^>]*autoplay/i.test(html));
});

test('viewer reveal button cannot override a disabled global blur setting', () => {
  const css = fs.readFileSync(path.join(__dirname, '../templates/viewer.css'), 'utf8');
  const rules = [...css.matchAll(/([^{}]+)\{([^{}]+)\}/g)];
  const revealRules = rules.filter(([, selector, declarations]) =>
    selector.includes('#lbNsfwReveal') && /display:\s*block/.test(declarations));
  assert.equal(revealRules.length, 1);
  assert.ok(revealRules[0][1].includes('body:not(.no-nsfw-blur)'));
  assert.ok(revealRules[0][1].includes(':not(.nsfw-revealed)'));
});

test('artwork actions target one post and stop card opening', () => {
  const post={source:'test',id:'1',url:'https://example.org/image.jpg'};
  let saved, downloaded, stopped=0;
  const h=helpers({allPosts:[post],galRendered:[]});
  h.doSaveSingle=p=>{saved=p};
  h.doDownload=posts=>{downloaded=posts};
  for(const action of ['save-art','download-art']){
    let handler;
    const button={dataset:{uiAction:action,uid:'test:1'},closest:()=>null,addEventListener:(_,fn)=>{handler=fn}};
    h.bindSecurityActions({querySelectorAll:()=>[button]});
    handler({stopPropagation(){stopped++}});
  }
  assert.equal(saved,post);
  assert.equal(downloaded.length,1);
  assert.equal(downloaded[0],post);
  assert.equal(stopped,2);
  for(const obsolete of ['selectedIds','toggleCard(','galSelectMode','role="checkbox"']) assert.ok(!html.includes(obsolete),obsolete);
});

test('viewer shortcuts do not steal Space from focused buttons', () => {
  let selected = 0, closed = 0, moved = 0;
  const context = vm.createContext({
    document: {getElementById: id => ({classList: {contains: () => id === 'lightbox'}})},
    lbMode: 'search', lbToggleSel: () => selected++, closeLb: () => closed++, lbStep: value => { moved += value; },
  });
  vm.runInContext(html.slice(html.indexOf('function onKeyDown(e)'), html.indexOf('// Artwork actions are individual;')), context);
  context.onKeyDown({key: ' ', target: {tagName: 'BUTTON'}, preventDefault() { throw Error('button activation intercepted'); }});
  assert.equal(selected, 0);
  context.onKeyDown({key: ' ', target: {tagName: 'DIV'}, preventDefault() {}});
  assert.equal(selected, 0);
  context.onKeyDown({key: 'ArrowRight', target: {tagName: 'DIV'}, preventDefault() {}});
  assert.equal(moved, 1);
  context.onKeyDown({key: 'Escape', target: {tagName: 'BUTTON'}});
  assert.equal(closed, 1);
});
