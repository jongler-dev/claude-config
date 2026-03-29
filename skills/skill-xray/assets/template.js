// Theme
function toggleTheme() {
  const html = document.documentElement;
  const lightIcon = document.querySelector('.theme-icon-light');
  const darkIcon = document.querySelector('.theme-icon-dark');
  if (html.getAttribute('data-theme') === 'dark') {
    html.removeAttribute('data-theme');
    lightIcon.style.display = '';
    darkIcon.style.display = 'none';
  } else {
    html.setAttribute('data-theme', 'dark');
    lightIcon.style.display = 'none';
    darkIcon.style.display = '';
  }
  initMermaid();
}

// Default to dark mode always
document.documentElement.setAttribute('data-theme', 'dark');
var _lightIcon = document.querySelector('.theme-icon-light');
var _darkIcon = document.querySelector('.theme-icon-dark');
if (_lightIcon) _lightIcon.style.display = 'none';
if (_darkIcon) _darkIcon.style.display = '';

// Main tabs
function switchTab(id, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if (btn) btn.classList.add('active');
  if (id === 'architecture') { setTimeout(initMermaid, 50); }
}

// Architecture toggle buttons
function switchSubTab(id, btn) {
  const parent = btn.closest('.tab-content');
  parent.querySelectorAll('.arch-toggle-btn').forEach(t => t.classList.remove('active'));
  parent.querySelectorAll('.sub-tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  // Re-render mermaid diagrams that were hidden when initMermaid last ran
  var tab = document.getElementById(id);
  var mermaids = tab.querySelectorAll('.mermaid');
  if (mermaids.length) {
    mermaids.forEach(function(m) {
      if (m.getAttribute('data-processed')) {
        m.removeAttribute('data-processed');
        m.innerHTML = m.getAttribute('data-original') || m.innerHTML;
      }
    });
    mermaid.run({ nodes: Array.from(mermaids) });
  }
}

// Zoom — scales the SVG/pre inside a wrapper so mermaid-inner can scroll
function zoom(btn, delta) {
  const inner = btn.closest('.mermaid-container').querySelector('.mermaid-inner');
  const target = inner.querySelector('svg') || inner.querySelector('pre');
  if (!target) return;
  // Wrap target in a zoom-wrapper on first zoom
  var wrapper = inner.querySelector('.zoom-wrapper');
  if (!wrapper) {
    wrapper = document.createElement('div');
    wrapper.className = 'zoom-wrapper';
    wrapper.dataset.origW = target.getBoundingClientRect().width;
    wrapper.dataset.origH = target.getBoundingClientRect().height;
    target.parentNode.insertBefore(wrapper, target);
    wrapper.appendChild(target);
  }
  let z = parseFloat(inner.dataset.zoom || 1) + delta;
  z = Math.max(0.3, Math.min(3, z));
  inner.dataset.zoom = z;
  target.style.transform = 'scale(' + z + ')';
  target.style.transformOrigin = 'top left';
  wrapper.style.width = Math.ceil(wrapper.dataset.origW * z) + 'px';
  wrapper.style.height = Math.ceil(wrapper.dataset.origH * z) + 'px';
}

function zoomReset(btn) {
  const inner = btn.closest('.mermaid-container').querySelector('.mermaid-inner');
  var wrapper = inner.querySelector('.zoom-wrapper');
  var target = wrapper ? wrapper.querySelector('svg') || wrapper.querySelector('pre')
                       : inner.querySelector('svg') || inner.querySelector('pre');
  if (!target) return;
  inner.dataset.zoom = 1;
  target.style.transform = 'scale(1)';
  if (wrapper) {
    wrapper.style.width = '';
    wrapper.style.height = '';
  }
}

// Copy single finding
function copyFinding(btn) {
  const finding = btn.closest('.finding');
  const severity = finding.querySelector('.severity').textContent;
  const title = finding.querySelector('strong').textContent;
  const detail = finding.querySelector('p').textContent;
  const text = '[' + severity + '] ' + title + '\n' + detail;
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '\u2713';
    setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
  });
}

// Copy all findings
function copyAllFindings() {
  const findings = document.querySelectorAll('#review .finding');
  let text = '';
  findings.forEach(f => {
    const severity = f.querySelector('.severity').textContent;
    const title = f.querySelector('strong').textContent;
    const detail = f.querySelector('p').textContent;
    text += '[' + severity + '] ' + title + '\n' + detail + '\n\n';
  });
  const btn = document.querySelector('.copy-all-btn');
  navigator.clipboard.writeText(text.trim()).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy All'; }, 1500);
  });
}

// Mermaid
function initMermaid() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  mermaid.initialize({
    startOnLoad: false,
    theme: isDark ? 'dark' : 'default',
    securityLevel: 'loose',
    flowchart: { htmlLabels: true, fontSize: 10 },
    sequence: { fontSize: 14 }
  });
  document.querySelectorAll('.mermaid[data-processed]').forEach(el => {
    el.removeAttribute('data-processed');
    el.innerHTML = el.getAttribute('data-original') || el.innerHTML;
  });
  mermaid.run();
}

// Store original mermaid source before first render
document.querySelectorAll('.mermaid').forEach(el => {
  el.setAttribute('data-original', el.innerHTML);
});

// Back to top visibility
const btt = document.getElementById('backToTop');
window.addEventListener('scroll', () => {
  if (window.scrollY > 300) {
    btt.classList.add('visible');
  } else {
    btt.classList.remove('visible');
  }
});

// Deep Dive file type filter
(function initFileFilters() {
  var container = document.getElementById('fileFilters');
  var cards = document.querySelectorAll('#fileCards .file-card');
  if (!container || !cards.length) return;

  var typeLabels = {
    'skill_definition': 'Skill Definition',
    'agent_prompt': 'Agents',
    'reference': 'References',
    'script': 'Scripts',
    'asset': 'Assets',
    'other': 'Other'
  };

  // Count cards per type
  var counts = {};
  cards.forEach(function(c) {
    var t = c.dataset.fileType || 'other';
    counts[t] = (counts[t] || 0) + 1;
  });

  // Only show filter bar if there are 2+ types
  var types = Object.keys(counts);
  if (types.length < 2) return;

  // "All" button
  var allBtn = document.createElement('button');
  allBtn.className = 'filter-btn active';
  allBtn.dataset.type = 'all';
  allBtn.innerHTML = 'All <span class="filter-count">' + cards.length + '</span>';
  allBtn.onclick = function() { filterFiles('all', this); };
  container.appendChild(allBtn);

  // Per-type buttons (in typeLabels order)
  Object.keys(typeLabels).forEach(function(type) {
    if (!counts[type]) return;
    var btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.dataset.type = type;
    btn.innerHTML = typeLabels[type] + ' <span class="filter-count">' + counts[type] + '</span>';
    btn.onclick = function() { filterFiles(type, this); };
    container.appendChild(btn);
  });
})();

function filterFiles(type, btn) {
  document.querySelectorAll('#fileFilters .filter-btn').forEach(function(b) { b.classList.remove('active'); });
  btn.classList.add('active');
  document.querySelectorAll('#fileCards .file-card').forEach(function(card) {
    card.style.display = (type === 'all' || card.dataset.fileType === type) ? '' : 'none';
  });
}

// Initial render
initMermaid();
