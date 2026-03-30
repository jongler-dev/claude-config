// Theme
function toggleTheme() {
  var html = document.documentElement;
  var lightIcon = document.querySelector('.theme-icon-light');
  var darkIcon = document.querySelector('.theme-icon-dark');
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

document.documentElement.setAttribute('data-theme', 'dark');
var _lightIcon = document.querySelector('.theme-icon-light');
var _darkIcon = document.querySelector('.theme-icon-dark');
if (_lightIcon) _lightIcon.style.display = 'none';
if (_darkIcon) _darkIcon.style.display = '';

// Main tabs
function switchTab(id, btn) {
  document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
  document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
  document.getElementById(id).classList.add('active');
  if (btn) btn.classList.add('active');
  if (id === 'how-it-works') { setTimeout(initMermaid, 50); }
}

// Sub-tabs (How It Works)
function switchSubTab(id, btn) {
  var parent = document.getElementById('how-it-works');
  if (!parent) return;
  parent.querySelectorAll('.sub-tab-btn').forEach(function(t) { t.classList.remove('active'); });
  parent.querySelectorAll('.sub-tab-content').forEach(function(t) { t.classList.remove('active'); });
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  // Re-render mermaid for newly visible diagrams
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

// Zoom
function zoom(btn, delta) {
  var inner = btn.closest('.mermaid-container').querySelector('.mermaid-inner');
  var target = inner.querySelector('svg') || inner.querySelector('pre');
  if (!target) return;
  var wrapper = inner.querySelector('.zoom-wrapper');
  if (!wrapper) {
    wrapper = document.createElement('div');
    wrapper.className = 'zoom-wrapper';
    wrapper.dataset.origW = target.getBoundingClientRect().width;
    wrapper.dataset.origH = target.getBoundingClientRect().height;
    target.parentNode.insertBefore(wrapper, target);
    wrapper.appendChild(target);
  }
  var z = parseFloat(inner.dataset.zoom || 1) + delta;
  z = Math.max(0.3, Math.min(3, z));
  inner.dataset.zoom = z;
  target.style.transform = 'scale(' + z + ')';
  target.style.transformOrigin = 'top left';
  wrapper.style.width = Math.ceil(wrapper.dataset.origW * z) + 'px';
  wrapper.style.height = Math.ceil(wrapper.dataset.origH * z) + 'px';
}

function zoomReset(btn) {
  var inner = btn.closest('.mermaid-container').querySelector('.mermaid-inner');
  var wrapper = inner.querySelector('.zoom-wrapper');
  var target = wrapper ? wrapper.querySelector('svg') || wrapper.querySelector('pre')
                       : inner.querySelector('svg') || inner.querySelector('pre');
  if (!target) return;
  inner.dataset.zoom = 1;
  target.style.transform = 'scale(1)';
  if (wrapper) { wrapper.style.width = ''; wrapper.style.height = ''; }
}

// Copy single finding
function copyFinding(btn) {
  var finding = btn.closest('.finding');
  var severity = finding.querySelector('.severity').textContent;
  var title = finding.querySelector('strong').textContent;
  var detail = finding.querySelector('p').textContent;
  var text = '[' + severity + '] ' + title + '\n' + detail;
  navigator.clipboard.writeText(text).then(function() {
    btn.textContent = '\u2713';
    setTimeout(function() { btn.textContent = 'Copy'; }, 1500);
  });
}

// Copy all visible findings
function copyAllFindings() {
  var findings = document.querySelectorAll('#review .finding');
  var text = '';
  findings.forEach(function(f) {
    if (f.style.display === 'none') return;
    var severity = f.querySelector('.severity').textContent;
    var title = f.querySelector('strong').textContent;
    var detail = f.querySelector('p').textContent;
    text += '[' + severity + '] ' + title + '\n' + detail + '\n\n';
  });
  var btn = document.querySelector('.copy-all-btn');
  navigator.clipboard.writeText(text.trim()).then(function() {
    btn.textContent = 'Copied!';
    setTimeout(function() { btn.textContent = 'Copy All'; }, 1500);
  });
}

// Finding filters — dual axis (severity + source)
var _activeSeverity = 'all';
var _activeSource = 'all';

function filterFindings(axis, value, btn) {
  if (axis === 'severity') _activeSeverity = value;
  if (axis === 'source') _activeSource = value;

  // Update button states
  var filterBar = document.querySelector('.finding-filters');
  if (filterBar) {
    filterBar.querySelectorAll('.finding-filter-btn').forEach(function(b) {
      var bAxis = b.dataset.axis;
      var bVal = b.dataset.value;
      if (bAxis === axis) {
        b.classList.toggle('active', bVal === value);
      }
    });
  }

  // Clear score bar highlights when source filter changes
  if (axis === 'source') {
    document.querySelectorAll('.score-bar[data-source]').forEach(function(bar) {
      bar.classList.remove('active');
    });
  }

  // Apply filter to findings
  document.querySelectorAll('#review .finding').forEach(function(f) {
    var sevMatch = _activeSeverity === 'all' || f.classList.contains(_activeSeverity);
    var srcMatch = _activeSource === 'all' || f.dataset.source === _activeSource;
    f.style.display = (sevMatch && srcMatch) ? '' : 'none';
  });
}

// Score bar click → filter findings by source
function clickScoreBar(source, btn) {
  // Toggle: if already active, clear filter
  var isActive = btn.classList.contains('active');
  document.querySelectorAll('.score-bar[data-source]').forEach(function(bar) {
    bar.classList.remove('active');
  });

  if (isActive) {
    _activeSource = 'all';
  } else {
    btn.classList.add('active');
    _activeSource = source;
  }

  // Update source filter buttons to match
  var filterBar = document.querySelector('.finding-filters');
  if (filterBar) {
    filterBar.querySelectorAll('.finding-filter-btn[data-axis="source"]').forEach(function(b) {
      b.classList.toggle('active', b.dataset.value === _activeSource);
    });
  }

  // Apply filter
  document.querySelectorAll('#review .finding').forEach(function(f) {
    var sevMatch = _activeSeverity === 'all' || f.classList.contains(_activeSeverity);
    var srcMatch = _activeSource === 'all' || f.dataset.source === _activeSource;
    f.style.display = (sevMatch && srcMatch) ? '' : 'none';
  });

  // Scroll to findings
  var actionItems = document.querySelector('.finding-filters');
  if (actionItems && !isActive) {
    actionItems.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// Mermaid
function initMermaid() {
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  mermaid.initialize({
    startOnLoad: false,
    theme: isDark ? 'dark' : 'default',
    securityLevel: 'loose',
    flowchart: { htmlLabels: true, fontSize: 10 },
    sequence: { fontSize: 14 }
  });
  document.querySelectorAll('.mermaid[data-processed]').forEach(function(el) {
    el.removeAttribute('data-processed');
    el.innerHTML = el.getAttribute('data-original') || el.innerHTML;
  });
  mermaid.run();
}

document.querySelectorAll('.mermaid').forEach(function(el) {
  el.setAttribute('data-original', el.innerHTML);
});

// Back to top
var btt = document.getElementById('backToTop');
window.addEventListener('scroll', function() {
  if (window.scrollY > 300) { btt.classList.add('visible'); }
  else { btt.classList.remove('visible'); }
});

// File type filters (File Breakdown sub-tab)
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

  var counts = {};
  cards.forEach(function(c) {
    var t = c.dataset.fileType || 'other';
    counts[t] = (counts[t] || 0) + 1;
  });

  var types = Object.keys(counts);
  if (types.length < 2) return;

  var allBtn = document.createElement('button');
  allBtn.className = 'filter-btn active';
  allBtn.dataset.type = 'all';
  allBtn.innerHTML = 'All <span class="filter-count">' + cards.length + '</span>';
  allBtn.onclick = function() { filterFiles('all', this); };
  container.appendChild(allBtn);

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
