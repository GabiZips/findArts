const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
(async () => {
 fs.mkdirSync('build/desktop-review', {recursive:true}); const browser = await chromium.launch({channel:process.platform==='win32'?'msedge':undefined,headless:true}); try {
 const page = await browser.newPage({viewport:{width:1440,height:900},locale:'pt-BR'});
 const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*', async route => {
  const url=new URL(route.request().url());
  if(url.hostname!=='artfinder.test') return route.abort();
  if(url.pathname==='/') return route.fulfill({contentType:'text/html',body:fs.readFileSync('templates/index.html','utf8')});
  if(url.pathname.startsWith('/ui/')) return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'application/javascript',body:fs.readFileSync(path.join('templates',path.basename(url.pathname)),'utf8')});
  const data={
   '/api/health':{ok:true,mobile:false}, '/api/sources':{sources:['danbooru','safebooru','pixiv'],unavailable_sources:[]},
   '/api/categories':{categories:{landscape:{label:'Paisagens',tags:'landscape',group:'Referências',color:'#a594ee'}}},
   '/api/stats':{total:0,disk_mb:0,by_source:{},by_category:{},by_rating:{}},
   '/api/collections':{collections:[]}, '/api/favorites':{favorites:[]},'/api/ratings':{ratings:{}},
   '/api/gallery':{images:[]},'/api/downloaded-ids':{ids:[]},'/api/search-stream':{posts:[],errors:[]},
   '/api/settings/credentials':{groups:[]}
  };
  return route.fulfill({contentType:'application/json',body:JSON.stringify(data[url.pathname]||{})});
 });
 await page.goto('http://artfinder.test');
 await page.waitForSelector('#srcGroup input',{state:'attached'});
 await page.screenshot({animations:'disabled',path:'build/desktop-review/home.png'});
 await page.getByRole('button',{name:'Nova busca',exact:true}).click();
 assert.equal(await page.locator('#desktopSearch').evaluate(el=>el.open),true);
 await page.locator('#btnSearch').click();
 assert.equal(await page.locator('#toast').evaluate(el=>el.closest('dialog')?.id),'desktopSearch');
 await page.locator('#catGroupsArea summary').click();
 await page.locator('input[name=cat]').check();
 await page.screenshot({animations:'disabled',path:'build/desktop-review/search.png'});
 await page.keyboard.press('Escape');
 assert.equal(await page.locator('#desktopSearch').evaluate(el=>el.open),false);
 assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Nova busca');
 await page.getByRole('button',{name:'Filtros',exact:true}).first().click();
 await page.locator('#scoreInput').fill('42'); await page.locator('#scoreInput').dispatchEvent('change');
 await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Nova busca',exact:true}).click();
 assert.equal(await page.locator('#scoreInput').inputValue(),'42');
 assert.equal(await page.locator('input[name=cat]').isChecked(),true);
 await page.locator('#btnSearch').click();
 assert.equal(await page.locator('#desktopSearch').evaluate(el=>el.open),false);
 await page.getByRole('button',{name:'Configurações',exact:true}).click();
 await page.screenshot({animations:'disabled',path:'build/desktop-review/settings.png'});
 await page.getByRole('button',{name:/Fontes e credenciais/}).click();
 assert.equal(await page.locator('#desktopSettings').evaluate(el=>el.open),false);
 assert.equal(await page.locator('#credentialModal').evaluate(el=>el.classList.contains('open')),true);
 await page.evaluate(()=>closeCredentialSettings());
 await page.getByRole('tab',{name:'Galeria',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('#pageGallery').classList.contains('active'));
 await page.screenshot({animations:'disabled',path:'build/desktop-review/gallery.png'});
 await page.getByRole('tab',{name:'Galeria',exact:true}).focus(); await page.keyboard.press('ArrowDown'); assert.equal(await page.getByRole('tab',{name:'Stats',exact:true}).getAttribute('aria-selected'),'true');
 await page.waitForFunction(()=>document.querySelector('#statsTotal').textContent==='0');
 await page.getByRole('tab',{name:'Buscar',exact:true}).click();
 await page.selectOption('#languageSelect','en');
 assert.equal(await page.locator('.desktop-heading h1').first().textContent(),'Explore artwork');
 await page.setViewportSize({width:800,height:650});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.setViewportSize({width:390,height:844}); await page.waitForFunction(()=>!document.body.classList.contains('desktop-workspace'));
 assert.equal(await page.locator('#sidebar').evaluate(el=>el.parentElement.className),'sidebar-wrap');
 await page.screenshot({animations:'disabled',path:'build/desktop-review/mobile.png'});
 await page.setViewportSize({width:1440,height:900}); await page.waitForFunction(()=>document.body.classList.contains('desktop-workspace'));
 await page.getByRole('button',{name:'New search',exact:true}).click();
 assert.equal(await page.locator('#desktopSearch input[name=cat]').isChecked(),true);
 await page.keyboard.press('Tab');
 assert.equal(await page.evaluate(()=>document.activeElement.closest('dialog')?.id),'desktopSearch');
 assert.deepEqual(errors,[]);
 console.log('PASS: dialogs, Escape/focus, state preservation, search, settings handoff, translations, responsive layout, no JS errors');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
