const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

async function run() {
  const output = 'build/legacy-review';
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({
    channel: process.platform === 'win32' ? 'msedge' : undefined,
    headless: true
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: 'pt-BR' });
    const errors = [];
    const assessmentRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      if (/\/api\/(ratings|rated-posts)$/.test(request.url())) assessmentRequests.push(request.url());
    });
    const fixture = {
      id: '1', source: 'danbooru', artist: 'Artista de teste', rating: 'sfw',
      url: 'https://media.test/art.png', width: 420, height: 520, score: 20
    };
    const data = {
      '/api/health': { ok: true, mobile: false },
      '/api/sources': { sources: ['danbooru'], unavailable_sources: [] },
      '/api/categories': { categories: { landscape: { label: 'Paisagens', tags: 'landscape', group: 'Referências' } } },
      '/api/stats': { total: 0 },
      '/api/collections': { collections: [] },
      '/api/favorites': { favorites: [] },
      '/api/gallery': { images: [] },
      '/api/downloaded-ids': { ids: [] },
      '/api/search-stream': { posts: [fixture], errors: [] }
    };
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.hostname !== 'artfinder.test') return route.abort();
      if (url.pathname === '/') {
        return route.fulfill({ contentType: 'text/html', body: fs.readFileSync('templates/index.html', 'utf8') });
      }
      if (url.pathname.startsWith('/ui/')) {
        const filename = path.basename(url.pathname);
        return route.fulfill({
          contentType: filename.endsWith('.css') ? 'text/css' : 'application/javascript',
          body: fs.readFileSync(path.join('templates', filename), 'utf8')
        });
      }
      if (url.pathname === '/api/proxy-image') {
        return route.fulfill({
          contentType: 'image/png',
          body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2iYAAAAASUVORK5CYII=', 'base64')
        });
      }
      return route.fulfill({ json: data[url.pathname] || {} });
    });
    await page.goto('http://artfinder.test');
    await page.locator('#srcGroup input').first().waitFor();
    assert.equal(await page.locator('#sidebar').evaluate(sidebar => sidebar.parentElement.className), 'sidebar-wrap');
    await page.locator('[data-stab="filtros"]').click();
    await page.locator('#sideFiltros [data-val="sfw"]').waitFor();
    assert.equal(await page.locator('[data-group="aval"]').count(), 0);
    await page.screenshot({ path: path.join(output, 'legacy-filters.png'), animations: 'disabled' });
    await page.locator('[data-stab="busca"]').click();
    await page.locator('#catGroupsArea summary').first().click();
    await page.locator('input[name="cat"]').first().check();
    await page.locator('#srcGroup input').first().check();
    await page.locator('#btnSearch').click();
    await page.locator('#grid .card').first().waitFor();
    assert.equal(await page.locator('#resultSourceFilter option[value="danbooru"]').count(), 1);
    await page.evaluate(() => openLb(0));
    await page.locator('#lightbox.open').waitFor();
    await page.keyboard.press('3');
    assert.equal(await page.locator('#lbRateBar').count(), 0);
    await page.keyboard.press('Escape');
    await page.getByRole('tab', { name: 'Galeria' }).click();
    await page.locator('#pageGallery.active').waitFor();
    assert.equal(await page.locator('#galViewRated, #galAvalFilter').count(), 0);
    await page.getByRole('tab', { name: 'Stats' }).click();
    await page.locator('#pageStats.active').waitFor();
    assert.equal(await page.locator('#statsTriagem').count(), 0);
    assert.deepEqual(assessmentRequests, []);
    assert.deepEqual(errors, []);
    console.log('PASS: legacy sidebar, filters, search, site selection, viewer, gallery and statistics without assessment controls or requests');
  } finally {
    await browser.close();
  }
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
