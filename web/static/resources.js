let allItems   = [];
let activeFilter = 'all';
let currentView  = 'grid';
let pendingDelId = null;

/* ── Source helpers ─────────────────────────────── */
const ICONS = {
  github_repo:'🐙', github_file:'🐙', github_gist:'🐙',
  youtube_video:'▶️', youtube_shorts:'▶️', youtube_playlist:'▶️',
  local_image:'🖼️', image_url:'🖼️',
  pdf_document:'📄', pdf_url:'📄',
  instagram_post:'📸', instagram_reel:'📸',
  web:'🌐', medium_article:'📝', substack_article:'📝',
  arxiv_paper:'🔬', reddit_post:'💬', reddit_subreddit:'💬',
  plain_text:'📋', plain_text_file:'📋',
  huggingface_model:'🤗', huggingface_dataset:'🤗',
};
const icon = s => ICONS[s] || '📎';

function badgeClass(s) {
  if (!s) return 'badge-default';
  if (s.startsWith('github'))    return 'badge-github';
  if (s.startsWith('youtube'))   return 'badge-youtube';
  if (s.includes('image'))       return 'badge-image';
  if (s.includes('text') || s === 'plain_text') return 'badge-text';
  if (s.includes('pdf'))         return 'badge-pdf';
  if (s.startsWith('instagram')) return 'badge-instagram';
  return 'badge-web';
}

function filterKey(s) {
  if (!s) return 'other';
  if (s.startsWith('github'))  return 'github';
  if (s.startsWith('youtube')) return 'youtube';
  if (s.includes('image'))     return 'image';
  if (s.includes('text') || s === 'plain_text') return 'text';
  return 'web';
}

function fmt(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-IN',
    { day:'numeric', month:'short', year:'numeric' });
}

function esc(str) {
  return String(str||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/'/g,'&#039;');
}

/* ── Load ───────────────────────────────────────── */
async function loadResources() {
  try {
    const r = await fetch('/api/resources?limit=500');
    const d = await r.json();
    allItems = d.resources || [];
    computeStats();
    render();
  } catch(e) {
    document.getElementById('itemsWrap').innerHTML =
      `<div class="empty"><div class="icon">⚠️</div>
       <h3>Could not load resources</h3><p>${e.message}</p></div>`;
  }
}

function computeStats() {
  document.getElementById('totalCount').textContent  = allItems.length;
  document.getElementById('githubCount').textContent = allItems.filter(i=>i.source?.startsWith('github')).length;
  document.getElementById('imageCount').textContent  = allItems.filter(i=>i.source?.includes('image')).length;
  document.getElementById('webCount').textContent    = allItems.filter(i=>filterKey(i.source)==='web').length;
  document.getElementById('ytCount').textContent     = allItems.filter(i=>i.source?.startsWith('youtube')).length;
}

/* ── Filter / View ──────────────────────────────── */
function setFilter(f, btn) {
  activeFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  render();
}

function setView(v) {
  currentView = v;
  document.getElementById('btnGrid').classList.toggle('on', v==='grid');
  document.getElementById('btnList').classList.toggle('on', v==='list');
  const wrap = document.getElementById('itemsWrap');
  wrap.className = v === 'grid' ? 'items-wrap grid-view' : 'items-wrap list-view';
  render();
}

/* ── Render ─────────────────────────────────────── */
function render() {
  const q   = document.getElementById('searchInput').value.toLowerCase();
  let items = allItems;
  if (activeFilter !== 'all')
    items = items.filter(i => filterKey(i.source) === activeFilter);
  if (q)
    items = items.filter(i =>
      (i.vault_title||i.title||'').toLowerCase().includes(q) ||
      (i.url||'').toLowerCase().includes(q) ||
      (i.source||'').toLowerCase().includes(q)
    );

  const wrap = document.getElementById('itemsWrap');
  if (!items.length) {
    wrap.innerHTML = `<div class="empty">
      <div class="icon">🗄️</div>
      <h3>Nothing here yet</h3>
      <p>Start by pasting a link or text in the chat.</p></div>`;
    return;
  }

  wrap.innerHTML = items.map((item) => {
    const num         = allItems.length - allItems.indexOf(item);
    const src         = item.source || 'unknown';
    const cardTitle   = item.vault_title || item.title || item.url || 'Untitled';
    const cardSnippet = item.vault_snippet || (item.llm_output||'').slice(0,160);
    const isGrid      = currentView === 'grid';

    return `
      <div class="card" data-id="${item.id}" onclick="openModal(${item.id})">
        <div class="card-header">
          <div class="card-icon">${icon(src)}</div>
          <div class="card-meta">
            <div class="card-num">#${num}</div>
            <div class="card-title">${esc(cardTitle)}</div>
            ${!isGrid ? `<span class="card-date">${fmt(item.created_at)}</span>` : ''}
          </div>
          <span class="card-badge ${badgeClass(src)}">${src.replace(/_/g,' ')}</span>
          <button class="card-del" title="Delete" onclick="askDel(event,${item.id})">🗑</button>
        </div>
        ${isGrid && cardSnippet ? `<div class="card-snippet">${esc(cardSnippet)}…</div>` : ''}
        ${isGrid ? `
        <div class="card-footer">
          <span><span class="status-dot ${item.status==='error'?'status-error':'status-success'}"></span>${item.status||'processed'}</span>
          <span>${fmt(item.created_at)}</span>
        </div>` : ''}
      </div>`;
  }).join('');
}

/* ── Modal popup ────────────────────────────────────── */
async function openModal(id) {
  const r    = await fetch(`/api/resources/${id}`);
  const item = await r.json();
  const src  = item.source || 'unknown';

  document.getElementById('mIcon').textContent  = icon(src);
  document.getElementById('mTitle').textContent = item.vault_title || item.title || item.url || 'Untitled';
  document.getElementById('mBadge').textContent = src.replace(/_/g,' ');
  document.getElementById('mBadge').className   = `card-badge ${badgeClass(src)}`;
  document.getElementById('mDate').textContent  = fmt(item.created_at);

  let rawHtml = '';
  let ri = null;
  try {
    ri = typeof item.raw_input === 'string' ? JSON.parse(item.raw_input) : item.raw_input;
  } catch(e) { ri = null; }

  if (ri) {
    if (ri.url) {
      const isRepo = src.startsWith('github');
      rawHtml += `
        <div class="section-label">URL</div>
        <div class="raw-block">
          ${isRepo
            ? `<a class="repo-path" href="${esc(ri.url)}" target="_blank" rel="noopener">🐙 ${esc(ri.url)}</a>`
            : `<a href="${esc(ri.url)}" target="_blank" rel="noopener">${esc(ri.url)}</a>`
          }
        </div>`;
    }

    if (item.files) {
      try {
        const f = JSON.parse(item.files);
        if (f.repo_path) {
          rawHtml += `
            <div class="section-label" style="margin-top:16px">Local Repo</div>
            <div class="raw-block"><span class="repo-path">📁 ${esc(f.repo_path)}</span></div>`;
        }
      } catch(e){}
    }

    if (ri.text) {
      rawHtml += `
        <div class="section-label" style="margin-top:16px">Text</div>
        <div class="raw-block">${esc(ri.text)}</div>`;
    }

    if (ri.image_path || ri.filename) {
      const filename = ri.filename || ri.image_path.split(/[\\/]/).pop();
      const imgSrc   = `/storage/images/${encodeURIComponent(filename)}`;
      rawHtml += `
        <div class="section-label" style="margin-top:16px">Image</div>
        <div class="raw-block">
          <code>${esc(ri.image_path || filename)}</code><br/>
          <img src="${imgSrc}" alt="${esc(filename)}"
            style="max-width:100%;border-radius:8px;margin-top:10px;border:1px solid var(--border)"
            onerror="this.style.display='none'" />
        </div>`;
    }
  } else if (item.raw_input) {
    rawHtml = `<div class="raw-block">${esc(String(item.raw_input))}</div>`;
  }

  if (!rawHtml && item.url) {
    rawHtml = `
      <div class="section-label">URL</div>
      <div class="raw-block">
        <a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.url)}</a>
      </div>`;
  }

  document.getElementById('tab-raw').innerHTML =
    rawHtml || '<div class="raw-block" style="color:var(--muted)">No raw input stored.</div>';

  const ans = item.llm_output || (item.error ? `⚠️ Error: ${item.error}` : 'No answer recorded.');
  document.getElementById('tab-answer').innerHTML = `<div class="llm-answer">${esc(ans)}</div>`;

  document.querySelectorAll('.tab').forEach((t,i)      => t.classList.toggle('active', i===0));
  document.querySelectorAll('.tab-panel').forEach((p,i) => p.classList.toggle('show',  i===0));

  document.getElementById('overlay').classList.add('show');
}

function maybeClose(e) {
  if (e.target === document.getElementById('overlay')) closeModal();
}
function closeModal() {
  document.getElementById('overlay').classList.remove('show');
}
function switchTab(name, btn) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('show'));
  document.getElementById('tab-'+name).classList.add('show');
}

/* ── Delete ─────────────────────────────────────── */
function askDel(e, id) {
  e.stopPropagation();
  pendingDelId = id;
  document.getElementById('delConfirm').style.display = 'flex';
}
function cancelDel() {
  pendingDelId = null;
  document.getElementById('delConfirm').style.display = 'none';
}
async function confirmDel() {
  if (!pendingDelId) return;
  try {
    await fetch(`/api/resources/${pendingDelId}`, { method: 'DELETE' });
    allItems = allItems.filter(i => i.id !== pendingDelId);
    computeStats();
    render();
  } catch(e) { alert('Delete failed: ' + e.message); }
  cancelDel();
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeModal(); cancelDel(); }
});

loadResources();