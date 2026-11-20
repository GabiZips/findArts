/* Desktop workspace. Reuses the existing controls and their state, never copies them. */
(() => {
  'use strict';
  const media = matchMedia('(min-width: 761px)');
  const sidebar = document.getElementById('sidebar');
  const home = sidebar.parentElement;
  const icon = (paths) => `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
  const icons = {
    add: icon('<path d="M12 5v14M5 12h14"/>'),
    filter: icon('<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="currentColor"/><circle cx="15" cy="17" r="3" fill="currentColor"/>'),
    folder: icon('<path d="M3 7V5a2 2 0 0 1 2-2h5l3 4h6a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>'),
    settings: icon('<circle cx="12" cy="12" r="3"/><path d="m10 3-1 3-3 1-3 3v4l3 3 3 1 1 3h4l1-3 3-1 3-3v-4l-3-3-3-1-1-3Z"/>'),
    close: icon('<path d="m6 6 12 12M6 18 18 6"/>'),
    art: icon('<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 6-6 4 4 3-3 5 5"/>'),
  };
  const button = (label, glyph, action, className = 'desktop-action') => {
    const el = document.createElement('button');
    el.type = 'button'; el.className = className;
    el.innerHTML = `${icons[glyph] || ''}<span>${label}</span>`;
    el.addEventListener('click', action);
    return el;
  };
  function dialog(id, title, subtitle) {
    const el = document.createElement('dialog');
    el.id = id; el.className = 'desktop-dialog';
    el.setAttribute('aria-labelledby', `${id}Title`);
    el.innerHTML = `<div class="desktop-dialog-head"><div><h2 id="${id}Title">${title}</h2><p>${subtitle}</p></div></div><div class="desktop-dialog-body"></div>`;
    const close = button('Fechar', 'close', () => el.close(), 'desktop-close');
    close.setAttribute('aria-label', 'Fechar');
    el.firstElementChild.append(close);
    // Native dialogs provide focus containment, Escape and focus restoration.
    el.addEventListener('click', e => {
      if(e.target !== el) return;
      const r = el.getBoundingClientRect();
      if(e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) el.close();
    });
    document.body.append(el);
    return el;
  }
  const search = dialog('desktopSearch', 'Nova busca', 'Escolha o conteúdo e as fontes para explorar.');
  const settings = dialog('desktopSettings', 'Configurações', 'Suas fontes, dispositivos e arquivos em um só lugar.');
  function updateSearchTitle(tab) {
    search.querySelector('h2').replaceChildren(document.createTextNode(tab === 'filtros' ? 'Filtros' : 'Nova busca'));
    search.querySelector('.desktop-dialog-head p').replaceChildren(document.createTextNode(tab === 'filtros' ? 'Ajuste os resultados sem precisar buscar de novo.' : 'Escolha o conteúdo e as fontes para explorar.'));
    applyTranslations(search);
  }
  sidebar.querySelectorAll('.side-tab').forEach(el => el.addEventListener('click', () => updateSearchTitle(el.dataset.stab)));
  function openSearch(tab = 'busca') {
    if(!media.matches) return;
    sidebar.classList.remove('collapsed');
    switchSideTab(tab);
    updateSearchTitle(tab);
    search.append(document.getElementById('toast'));
    search.showModal();
  }
  search.addEventListener('close', () => document.body.append(document.getElementById('toast')));
  window.desktopUI = {get enabled(){return media.matches;}, openSearch, closeSearch: () => search.close()};
  const settingsBody = settings.querySelector('.desktop-dialog-body');
  [
    ['Fontes e credenciais', 'Conecte os sites que você usa para encontrar artes.', 'settings', openCredentialSettings],
    ['Parear PC e celular', 'Leve suas categorias e fontes para o celular.', 'folder', openPairing],
    ['Downloads', 'Abra a pasta das artes baixadas.', 'folder', () => openNativeFolder('downloads')],
    ['Pastas do aplicativo', 'Acesse os dados e as configurações locais.', 'folder', () => openNativeFolder('data')],
  ].forEach(([title, description, glyph, action]) => {
    const el = button(title, glyph, () => {settings.close(); action();}, 'desktop-setting');
    const desc = document.createElement('small'); desc.textContent = description;
    el.querySelector('span').append(desc); settingsBody.append(el);
  });
  const rail = document.createElement('div'); rail.className = 'desktop-rail-actions desktop-only';
  rail.append(button('Categorias', 'folder', openCatManager), button('Configurações', 'settings', () => settings.showModal()));
  document.querySelector('header .tabs').after(rail);
  const navigation = document.querySelector('header .tabs');
  navigation.addEventListener('keydown', event => {
    if(!media.matches || !['ArrowDown','ArrowUp','Home','End'].includes(event.key)) return;
    const tabs = [...navigation.querySelectorAll('.tab')];
    const current = tabs.indexOf(document.activeElement);
    if(current < 0) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + tabs.length) % tabs.length;
    tabs[next].focus(); tabs[next].click();
  });
  const heading = document.createElement('div'); heading.className = 'desktop-heading desktop-only';
  heading.innerHTML = '<div><h1>Explorar artes</h1><p>Encontre sua próxima inspiração.</p></div><div class="desktop-heading-actions"></div>';
  const actions = heading.querySelector('.desktop-heading-actions');
  actions.append(button('Filtros', 'filter', () => openSearch('filtros')), button('Nova busca', 'add', () => openSearch(), 'desktop-primary'));
  document.querySelector('#pageSearch main').prepend(heading);
  document.getElementById('searchProgress').append(button('Cancelar', 'close', cancelSearch, 'desktop-action desktop-only'));
  for(const [id, title, subtitle] of [['pageGallery','Sua galeria','As artes que você escolheu guardar.'],['pageStats','Sua biblioteca em números','Acompanhe suas artes e organize seus arquivos.']]) {
    const h = document.createElement('div'); h.className = 'desktop-heading desktop-only';
    h.innerHTML = `<div><h1>${title}</h1><p>${subtitle}</p></div>`;
    document.getElementById(id).prepend(h);
  }
  const empty = document.getElementById('emptyState');
  const welcome = document.createElement('div'); welcome.className = 'desktop-welcome desktop-only';
  welcome.innerHTML = `<div class="desktop-art-mark">${icons.art}</div><h2>Um espaço para suas descobertas</h2><p>Escolha personagens, artistas e fontes.<br>Suas próximas referências começam aqui.</p>`;
  welcome.append(button('Criar uma busca', 'add', () => openSearch(), 'desktop-primary'));
  empty.append(welcome);
  // Close the native dialog before opening the existing category editor.
  sidebar.querySelector('.cat-manager-btn').addEventListener('click', () => search.close(), true);
  function syncLayout() {
    document.body.classList.toggle('desktop-workspace', media.matches);
    document.querySelector('header .tabs').setAttribute('aria-orientation', media.matches ? 'vertical' : 'horizontal');
    search.close(); settings.close();
    if(media.matches) {
      search.querySelector('.desktop-dialog-body').append(sidebar);
      sidebar.classList.remove('collapsed');
      document.body.classList.remove('sidebar-open');
    } else {
      home.append(sidebar);
      sidebarCollapsed = true;
      sidebar.classList.add('collapsed');
      document.body.classList.remove('sidebar-open');
    }
  }
  media.addEventListener('change', syncLayout);
  syncLayout();
  applyTranslations(document);
})();
