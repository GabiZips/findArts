const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('templates/index.html', 'utf8');
function setup() {
  const select = {value: '', innerHTML: ''};
  const context = vm.createContext({document: {getElementById: () => select}, t: x => x, esc: x => String(x).replaceAll('"', '&quot;').replaceAll('<', '&lt;')});
  vm.runInContext(html.slice(html.indexOf('function artworkSource('), html.indexOf('function getFilteredPosts(')), context);
  return {context, select};
}
test('site selection handles aliases and all-sites without mutating the collection', () => {
  const {context} = setup();
  const items = [{source: 'bsky'}, {source: 'Bluesky'}, {source: 'pixiv'}, {source: ''}];
  assert.deepEqual(context.filterBySource(items, 'bluesky'), items.slice(0, 2));
  assert.deepEqual(context.filterBySource(items, 'pixiv'), [items[2]]);
  assert.deepEqual(context.filterBySource(items, ''), items);
  assert.equal(context.filterBySource(items, 'e621').length, 0);
  assert.equal(items.length, 4);
});
test('streamed results and refresh preserve selected site and safely build options', () => {
  const {context, select} = setup();
  select.value = 'pixiv';
  context.syncSourceFilter('filter', [{source: 'bsky'}, {source: 'Bluesky'}, {source: '<img"'}]);
  assert.equal(select.value, 'pixiv');
  assert.ok(select.innerHTML.includes('value="pixiv"'));
  assert.equal((select.innerHTML.match(/value="bluesky"/g)||[]).length, 1);
  assert.ok(!select.innerHTML.includes('<img'));
});
