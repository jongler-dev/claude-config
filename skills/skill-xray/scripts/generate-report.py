#!/usr/bin/env python3
"""Generate skill-xray HTML report from analysis.json + review.json + template."""

import json
import html
import os
import re
import sys
from datetime import date


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_text(path):
    with open(path) as f:
        return f.read()


# ---------------------------------------------------------------------------
# JSON validation
# ---------------------------------------------------------------------------

ANALYSIS_REQUIRED_KEYS = [
    'skill_name', 'skill_path', 'metadata', 'file_tree', 'total_lines',
    'total_files', 'tools_used', 'execution_flow', 'file_analysis',
    'external_interactions', 'mermaid_sequence', 'mermaid_flowchart',
    'summary', 'deep_dive',
]

REVIEW_REQUIRED_KEYS = [
    'spec_compliance', 'security_findings', 'best_practices',
    'scores', 'grade', 'grade_assessment', 'grade_strengths',
    'grade_improvements',
]

REVIEW_SCORE_KEYS = [
    'structure', 'spec_compliance', 'security', 'quality',
    'best_practices', 'overall',
]


def validate_analysis(data):
    errors = []
    for key in ANALYSIS_REQUIRED_KEYS:
        if key not in data:
            errors.append(f'analysis.json: missing required key "{key}"')
    return errors


def validate_review(data):
    errors = []
    for key in REVIEW_REQUIRED_KEYS:
        if key not in data:
            errors.append(f'review.json: missing required key "{key}"')

    scores = data.get('scores', {})
    for key in REVIEW_SCORE_KEYS:
        if key not in scores:
            errors.append(f'review.json: scores missing "{key}"')
        elif not isinstance(scores[key], (int, float)):
            errors.append(f'review.json: scores.{key} must be a number, got {type(scores[key]).__name__}')

    if not isinstance(data.get('grade_strengths', None), list):
        errors.append('review.json: grade_strengths must be an array')
    if not isinstance(data.get('grade_improvements', None), list):
        errors.append('review.json: grade_improvements must be an array')

    grade = data.get('grade', '')
    if grade not in ('A', 'B', 'C', 'D', 'F'):
        errors.append(f'review.json: grade must be A/B/C/D/F, got "{grade}"')

    return errors


# ---------------------------------------------------------------------------
# Markdown -> HTML (handles the subset the analyzer produces)
# ---------------------------------------------------------------------------

def md_to_html(md_text):
    lines = md_text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Horizontal rule
        if re.match(r'^---+$', line.strip()):
            i += 1
            continue

        # Code block
        if line.strip().startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(html.escape(lines[i]))
                i += 1
            i += 1  # skip closing ```
            out.append(f'<pre><code>{chr(10).join(code_lines)}</code></pre>')
            continue

        # Table
        if '|' in line and line.strip().startswith('|'):
            table_lines = []
            while i < len(lines) and '|' in lines[i] and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            out.append(render_table(table_lines))
            continue

        # Headers
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = min(len(m.group(1)) + 1, 6)  # ## -> h3, ### -> h4
            out.append(f'<h{level}>{inline_md(m.group(2))}</h{level}>')
            i += 1
            continue

        # Unordered list
        if re.match(r'^[\s]*[-*]\s', line):
            items = []
            while i < len(lines) and re.match(r'^[\s]*[-*]\s', lines[i]):
                items.append(re.sub(r'^[\s]*[-*]\s', '', lines[i]))
                i += 1
            out.append('<ul>' + ''.join(f'<li>{inline_md(it)}</li>' for it in items) + '</ul>')
            continue

        # Ordered list
        if re.match(r'^[\s]*\d+\.\s', line):
            items = []
            while i < len(lines) and re.match(r'^[\s]*\d+\.\s', lines[i]):
                items.append(re.sub(r'^[\s]*\d+\.\s', '', lines[i]))
                i += 1
            out.append('<ol>' + ''.join(f'<li>{inline_md(it)}</li>' for it in items) + '</ol>')
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Paragraph (collect consecutive non-empty lines)
        para = []
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('#') \
                and not lines[i].strip().startswith('```') and not lines[i].strip().startswith('|') \
                and not re.match(r'^[\s]*[-*]\s', lines[i]) and not re.match(r'^---+$', lines[i].strip()):
            para.append(lines[i])
            i += 1
        out.append(f'<p>{inline_md(" ".join(para))}</p>')

    return '\n'.join(out)


def inline_md(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def render_table(lines):
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    if len(rows) < 2:
        return ''
    header = rows[0]
    data = [r for r in rows[1:] if not all(re.match(r'^[-:]+$', c) for c in r)]
    out = '<table><thead><tr>'
    for h in header:
        out += f'<th>{inline_md(h)}</th>'
    out += '</tr></thead><tbody>'
    for row in data:
        out += '<tr>'
        for c in row:
            out += f'<td>{inline_md(c)}</td>'
        out += '</tr>'
    out += '</tbody></table>'
    return out


# ---------------------------------------------------------------------------
# Placeholder generators
# ---------------------------------------------------------------------------

def sanitize_mermaid_sequence(text):
    """Escape HTML-like angle brackets in mermaid sequence diagram text."""
    # Replace <word> patterns that would be parsed as HTML tags
    text = re.sub(r'<(\w[\w-]*)>', r'#lt;\1#gt;', text)
    return text


def sanitize_mermaid_flowchart(text):
    """Quote flowchart node labels containing __ to prevent mermaid markdown parsing."""
    def _quote_bracket(m):
        return m.group(1) + '["' + m.group(2) + '"]' if '__' in m.group(2) else m.group(0)

    def _quote_brace(m):
        return m.group(1) + '{"' + m.group(2) + '"}' if '__' in m.group(2) else m.group(0)

    def _quote_paren(m):
        return m.group(1) + '("' + m.group(2) + '")' if '__' in m.group(2) else m.group(0)

    text = re.sub(r'(\w)\[([^\]"]+)\]', _quote_bracket, text)
    text = re.sub(r'(\w)\{([^}"]+)\}', _quote_brace, text)
    text = re.sub(r'(\w)\(([^)"]+)\)', _quote_paren, text)
    return text


def gen_header_source(analysis):
    git_url = analysis.get('git_url')
    if git_url:
        escaped = html.escape(git_url)
        return f'GitHub URL: <a href="{escaped}" target="_blank" rel="noopener">{escaped}</a>'
    path = html.escape(analysis['skill_path'])
    return f'Local path: <a href="file://{path}" target="_blank">{path}</a>'


def gen_summary_oneliner(analysis):
    summary = analysis.get('summary', '')
    m = re.match(r'^(.+?\.)\s', summary)
    return html.escape(m.group(1) if m else summary)


def _strip_heavy_parens(text):
    """Strip parenthetical content longer than 40 chars to keep prose scannable."""
    cleaned = re.sub(r'\s*\([^)]{40,}\)', '', text)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    # Fix dangling commas before "and"/"or" left by removal
    cleaned = re.sub(r',(\s+and\b)', r'\1', cleaned)
    cleaned = re.sub(r',(\s*\.)', r'\1', cleaned)
    return cleaned


def gen_overview_summary(analysis):
    summary = analysis.get('summary', '')
    m = re.match(r'^.+?\.\s+(.*)', summary, re.DOTALL)
    rest = m.group(1) if m else ''
    if not rest:
        return f'<p>{html.escape(summary)}</p>'

    sentences = re.split(r'(?<=[.!?])\s+', rest.strip())
    parts = []
    for s in sentences:
        parts.append(f'<p>{html.escape(_strip_heavy_parens(s))}</p>')
    return '\n'.join(parts)


def is_mcp_tool(name):
    return name.startswith('mcp__') or name.startswith('mcp_')


def _gen_badges(analysis, predicate, css_class):
    tools = [t for t in analysis.get('tools_used', []) if predicate(t.get('tool', ''))]
    if not tools:
        return ''
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in tools:
        name = t.get('tool', '')
        if name not in seen:
            seen.add(name)
            unique.append(t)
    return ' '.join(f'<span class="badge {css_class}">{html.escape(t["tool"])}</span>' for t in unique)


def gen_tools_section(analysis):
    allowed = analysis.get('metadata', {}).get('allowed_tools', [])
    allowed_set = set(allowed)
    # Exclude MCP tools (shown in External Resources) and tools already declared in frontmatter
    undeclared_html = _gen_badges(analysis, lambda name: not is_mcp_tool(name) and name not in allowed_set, 'undeclared')

    # Filter MCP tools out of frontmatter badges
    non_mcp_allowed = [t for t in allowed if not is_mcp_tool(t)]

    out = ''

    # Declared in frontmatter row (only non-MCP tools)
    if non_mcp_allowed:
        badges = ' '.join(f'<span class="badge tool">{html.escape(t)}</span>' for t in non_mcp_allowed)
        out += f'<div class="tools-columns" style="margin-bottom:0.75rem"><div class="tools-column"><h4 style="white-space:nowrap">Declared in SKILL.md</h4><div>{badges}</div></div></div>'

    # Used but not declared
    if undeclared_html:
        out += f'<div class="tools-column"><h4>Used but not Declared</h4><div>{undeclared_html}</div></div>'
    elif not non_mcp_allowed:
        out += '<p class="ext-none">None detected</p>'

    return out


def gen_file_tree(analysis):
    skill_name = analysis.get('skill_name', 'skill')
    files = analysis.get('file_tree', [])

    # Build a nested dict representing the directory tree
    tree = {}  # dir_name -> list of (filename, size)
    root_files = []  # (filename, size) for files at the root level

    for f in files:
        path = f.get('path', '')
        size = f.get('size_bytes', 0)
        if '/' in path:
            dir_name, file_name = path.split('/', 1)
            tree.setdefault(dir_name, []).append((file_name, size))
        else:
            root_files.append((path, size))

    # Build output lines: root files first, then directories
    lines = [f'{skill_name}/']
    entries = []  # (is_dir, name, children_or_size)
    for name, size in root_files:
        entries.append((False, name, size))
    for dir_name in sorted(tree.keys()):
        entries.append((True, dir_name, tree[dir_name]))

    for idx, entry in enumerate(entries):
        is_last = idx == len(entries) - 1
        connector = '└── ' if is_last else '├── '
        if entry[0]:  # directory
            dir_name, children = entry[1], entry[2]
            lines.append(f'{connector}{dir_name}/')
            child_prefix = '    ' if is_last else '│   '
            for cidx, (child_name, child_size) in enumerate(children):
                child_connector = '└── ' if cidx == len(children) - 1 else '├── '
                lines.append(f'{child_prefix}{child_connector}{child_name}')
        else:  # file
            name, size = entry[1], entry[2]
            lines.append(f'{connector}{name}')

    # Build aria-label summary
    total = len(files)
    dir_count = len(tree)
    dir_parts = []
    for name, size in root_files:
        dir_parts.append(name)
    for dir_name in sorted(tree.keys()):
        n = len(tree[dir_name])
        dir_parts.append(f'{dir_name}/ with {n} file{"s" if n != 1 else ""}')
    label = f'File tree: {total} files'
    if dir_count:
        label += f' in {dir_count} {"directories" if dir_count != 1 else "directory"}'
    label += ' — ' + ', '.join(dir_parts)

    return f'<div class="file-tree" role="img" aria-label="{html.escape(label)}">' + '\n'.join(lines) + '</div>'


def gen_design_decisions(analysis):
    """Extract the design decisions section from deep_dive markdown."""
    text = analysis.get('deep_dive', '')
    if not text:
        return ''
    # Find a section with "design" in the heading (case-insensitive)
    sections = re.split(r'^## ', text, flags=re.MULTILINE)
    for section in sections:
        first_line = section.split('\n', 1)[0].strip()
        if 'design' in first_line.lower():
            body = section.split('\n', 1)[1].strip() if '\n' in section else ''
            if body:
                return (
                    '<div class="card">'
                    '<h3>Design Decisions</h3>'
                    f'<div class="prose">{md_to_html(body)}</div>'
                    '</div>'
                )
    return ''


def gen_file_analysis_cards(analysis):
    files = analysis.get('file_analysis', [])
    if not files:
        return '<div class="card file-card"><p style="color:var(--text-muted)">No file analysis available.</p></div>'

    # Build type lookup from file_tree
    type_lookup = {}
    for ft in analysis.get('file_tree', []):
        type_lookup[ft.get('path', '')] = ft.get('type', 'other')

    cards = []
    for f in files:
        raw_path = f.get('path', '')
        path = html.escape(raw_path)
        purpose = html.escape(f.get('purpose', ''))
        loaded_when = html.escape(f.get('loaded_when', ''))
        key_sections = f.get('key_sections', [])
        references = f.get('references_files', [])
        file_type = html.escape(type_lookup.get(raw_path, 'other'))

        inner = f'<div class="file-card-purpose">{purpose}</div>'

        if key_sections:
            badges = ' '.join(f'<span class="badge tool">{html.escape(s)}</span>' for s in key_sections)
            inner += f'<div class="file-card-row"><span class="file-card-label">Key sections</span><div>{badges}</div></div>'

        if references:
            refs_list = ''.join(f'<li><code>{html.escape(r)}</code></li>' for r in references)
            inner += f'<div class="file-card-row"><span class="file-card-label">References</span><ul class="file-card-list">{refs_list}</ul></div>'

        if loaded_when:
            inner += f'<div class="file-card-row"><span class="file-card-label">Loaded</span><div>{loaded_when}</div></div>'

        cards.append(
            f'<div class="card file-card" data-file-type="{file_type}">'
            f'<h3 class="file-card-path">{path}</h3>'
            f'{inner}'
            f'</div>'
        )

    return '\n'.join(cards)


def score_color(n):
    if n >= 80:
        return 'var(--green)'
    elif n >= 60:
        return 'var(--yellow)'
    return 'var(--red)'


def gen_score_bars(review):
    scores = review.get('scores', {})
    categories = [
        ('Structure', 'structure'),
        ('Spec Compliance', 'spec_compliance'),
        ('Security', 'security'),
        ('Quality', 'quality'),
        ('Best Practices', 'best_practices'),
        ('Overall', 'overall'),
    ]
    bars = []
    for label, key in categories:
        n = scores.get(key, 0)
        color = score_color(n)
        is_overall = key == 'overall'
        cls = 'score-bar score-bar-overall' if is_overall else 'score-bar'
        bars.append(
            f'<div class="{cls}">'
            f'<label>{label}</label>'
            f'<div class="score-track"><div class="score-fill" style="width: {n}%; background: {color}"></div></div>'
            f'<span class="score-value">{n}</span>'
            f'</div>'
        )
    return '\n'.join(bars)


def gen_grade_assessment(review):
    return f'<p>{html.escape(review.get("grade_assessment", ""))}</p>'


def gen_grade_strengths(review):
    items = review.get('grade_strengths', [])
    if not items:
        return '<p style="color:var(--text-muted)">None identified</p>'
    return '<ul>' + ''.join(f'<li>{html.escape(s)}</li>' for s in items) + '</ul>'


def gen_grade_improvements(review):
    items = review.get('grade_improvements', [])
    if not items:
        return '<p style="color:var(--text-muted)">None identified</p>'
    return '<ul>' + ''.join(f'<li>{html.escape(s)}</li>' for s in items) + '</ul>'


def _linkify_url(name):
    """Wrap a URL string in an <a> tag if it looks like a URL."""
    if name.startswith(('http://', 'https://')):
        escaped = html.escape(name)
        return f'<a href="{escaped}" target="_blank" rel="noopener">{escaped}</a>'
    return html.escape(name)


def _ext_section(title, items, name_key, desc_key='purpose', str_parser=None):
    parts = [f'<div class="ext-section"><h4>{title}</h4>']
    if items:
        parts.append('<ul>')
        for item in items:
            if isinstance(item, str):
                name, desc = (str_parser(item) if str_parser else (item, ''))
                parts.append(f'<li><div class="ext-item-name">{_linkify_url(name)}</div>')
                if desc:
                    parts.append(f'<div class="ext-item-desc">{html.escape(desc)}</div>')
                parts.append('</li>')
            else:
                raw_name = item.get(name_key, '')
                parts.append(f'<li><div class="ext-item-name">{_linkify_url(raw_name)}</div>'
                             f'<div class="ext-item-desc">{html.escape(item.get(desc_key, ""))}</div></li>')
        parts.append('</ul>')
    else:
        parts.append('<p class="ext-none">None detected</p>')
    parts.append('</div>')
    return '\n'.join(parts)


def _parse_parenthesized(s):
    m = re.match(r'^(.+?)\s*\((.+)\)$', s)
    return (m.group(1).strip(), m.group(2)) if m else (s, '')


def _parse_dash_separated(s):
    parts = s.split(' - ', 1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else '')


def gen_secret_alerts(inventory):
    """Generate the secret scan alert banner and hit details for the review tab."""
    scan = inventory.get('secret_scan', {})
    hits = scan.get('hits', [])

    if not hits:
        return ''

    count = len(hits)
    noun = 'secret' if count == 1 else 'secrets'

    # Group hits by category for the summary
    categories = {}
    for h in hits:
        cat = h.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    cat_labels = {
        'cloud': 'Cloud Provider',
        'platform': 'Platform Token',
        'crypto': 'Cryptographic Material',
        'connection': 'Connection String',
        'generic': 'Hardcoded Secret',
        'entropy': 'High-Entropy String',
    }

    cat_summary = ', '.join(
        f'{v} {cat_labels.get(k, k)}'
        for k, v in sorted(categories.items(), key=lambda x: -x[1])
    )

    # Banner
    out = (
        f'<div class="secret-alert">'
        f'<div class="secret-alert-header">'
        f'<span class="secret-alert-icon">&#9888;</span>'
        f'<strong>{count} potential {noun} detected</strong>'
        f'<span class="secret-alert-cats">{html.escape(cat_summary)}</span>'
        f'</div>'
        f'<div class="secret-alert-hits">'
    )

    for h in hits:
        cat_class = h.get('category', 'unknown')
        out += (
            f'<div class="secret-hit">'
            f'<span class="secret-hit-loc">{html.escape(h["file"])}:{h["line"]}</span>'
            f'<span class="badge secret-cat-{html.escape(cat_class)}">{html.escape(h["label"])}</span>'
            f'<code class="secret-hit-redacted">{html.escape(h["redacted"])}</code>'
            f'</div>'
        )

    out += '</div></div>'
    return out


def gen_external_interactions(analysis):
    ext = analysis.get('external_interactions', {})
    return '\n'.join([
        _ext_section('URLs', ext.get('urls', []), 'url'),
        _ext_section('File System Paths', ext.get('filesystem_paths', []), 'path',
                     str_parser=_parse_parenthesized),
        _ext_section('External Access Tools', ext.get('external_tools', []), 'tool',
                     str_parser=_parse_dash_separated),
    ])


def normalize_severity(status):
    if status in ('fail', 'error'):
        return 'error'
    if status in ('warn', 'warning'):
        return 'warning'
    return 'info'


def _normalize_title(title):
    """Normalize a finding title for dedup comparison."""
    return re.sub(r'[^a-z0-9]', '', title.lower())


def _extract_keywords(normalized):
    """Extract meaningful keywords (4+ chars) from a normalized alphanumeric string.

    Since normalized strings have no separators, we use a sliding window to find
    common domain terms, then fall back to 4-gram chunks.
    """
    # Known domain terms to look for in the concatenated string
    _DOMAIN_TERMS = [
        'allowedtools', 'allowed', 'tools', 'example', 'examples', 'input',
        'output', 'inputs', 'outputs', 'security', 'description', 'trigger',
        'script', 'scripts', 'bash', 'network', 'secret', 'credential',
        'metadata', 'license', 'compatibility', 'name', 'restrict',
        'restriction', 'scope', 'scoped', 'scoping', 'trust', 'surface',
    ]
    found = set()
    for term in _DOMAIN_TERMS:
        if term in normalized:
            found.add(term)
    return found


def _is_duplicate(new_finding, existing_findings):
    """Check if a finding is a duplicate using keyword overlap and substring matching."""
    new_norm = _normalize_title(new_finding['title'])
    new_keywords = _extract_keywords(new_norm)

    for f in existing_findings:
        existing_norm = _normalize_title(f['title'])

        # Original substring check
        if len(new_norm) > 5 and len(existing_norm) > 5:
            if new_norm in existing_norm or existing_norm in new_norm:
                return True

        # Keyword overlap check: if both have 2+ keywords and share most of them
        if new_keywords:
            existing_keywords = _extract_keywords(existing_norm)
            if existing_keywords:
                overlap = new_keywords & existing_keywords
                smaller = min(len(new_keywords), len(existing_keywords))
                if smaller >= 2 and len(overlap) >= smaller * 0.6:
                    return True

    return False


def _add_findings(findings, items, source, title_key='title', severity_key='severity',
                   status_mode=False):
    """Add findings from a review section, with dedup and source tagging.

    Args:
        status_mode: If True, treat items as spec_compliance (status field, skip pass/n/a).
                     If False, treat as severity-based (skip info).
    """
    for item in items:
        if status_mode:
            status = item.get('status', '').lower()
            if status in ('pass', 'n/a'):
                continue
            sev = normalize_severity(status)
        else:
            sev = normalize_severity(item.get(severity_key, 'info'))
            if sev == 'info':
                continue

        finding = {
            'severity': sev,
            'source': source,
            'title': item.get(title_key, ''),
            'detail': item.get('detail', ''),
        }
        if not _is_duplicate(finding, findings):
            findings.append(finding)


SOURCE_LABELS = {
    'spec': 'Spec',
    'security': 'Security',
    'best-practice': 'Best Practice',
    'judgment': 'Judgment',
}


def gen_findings(review):
    findings = []

    _add_findings(findings, review.get('spec_compliance', []),
                  'spec', title_key='rule', status_mode=True)
    _add_findings(findings, review.get('security_findings', []), 'security')
    _add_findings(findings, review.get('best_practices', []), 'best-practice')
    _add_findings(findings, review.get('judgment_findings', []), 'judgment')

    # Sort: errors -> warnings
    order = {'error': 0, 'warning': 1}
    findings.sort(key=lambda f: order.get(f['severity'], 2))

    # Count
    errors = sum(1 for f in findings if f['severity'] == 'error')
    warnings = sum(1 for f in findings if f['severity'] == 'warning')

    # Spec compliance pass rate (excluding n/a)
    spec_rules = review.get('spec_compliance', [])
    applicable = [r for r in spec_rules if r.get('status') != 'n/a']
    passed = sum(1 for r in applicable if r.get('status') == 'pass')
    total_applicable = len(applicable)

    # Summary line
    parts = []
    if errors:
        parts.append(f'<a href="#finding-errors" class="count-error">{errors} error{"s" if errors != 1 else ""}</a>')
    if warnings:
        parts.append(f'<a href="#finding-warnings" class="count-warning">{warnings} warning{"s" if warnings != 1 else ""}</a>')
    if total_applicable:
        parts.append(f'<span class="count-pass">{passed} of {total_applicable} spec rules passed</span>')

    out = f'<div class="findings-summary">{" &middot; ".join(parts)}</div>\n'

    # Individual findings
    first_error = first_warning = True
    for f in findings:
        sev = f['severity']
        anchor_id = ''
        if sev == 'error' and first_error:
            anchor_id = ' id="finding-errors"'
            first_error = False
        elif sev == 'warning' and first_warning:
            anchor_id = ' id="finding-warnings"'
            first_warning = False

        sev_label = sev.capitalize()
        source_key = f.get('source', '')
        source_label = SOURCE_LABELS.get(source_key, '')
        source_html = f'<span class="finding-source finding-source-{source_key}">{source_label}</span>' if source_label else ''
        out += (
            f'<div class="finding {sev}" data-source="{source_key}"{anchor_id}>'
            f'<button class="copy-btn" onclick="copyFinding(this)">Copy</button>'
            f'<div class="severity">{sev_label} {source_html}</div>'
            f'<strong>{html.escape(f["title"])}</strong>'
            f'<p>{html.escape(f["detail"])}</p>'
            f'</div>\n'
        )

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 4:
        print(f'Usage: {sys.argv[0]} <analysis.json> <review.json> <built-template.html>', file=sys.stderr)
        print(f'  Writes report.html to the same directory as analysis.json', file=sys.stderr)
        sys.exit(1)

    analysis_path, review_path, template_path = sys.argv[1], sys.argv[2], sys.argv[3]

    analysis = load_json(analysis_path)
    review = load_json(review_path)
    template = load_text(template_path)

    # Load file-inventory.json from the same directory for secret scan results
    out_dir = os.path.dirname(analysis_path)
    inventory_path = os.path.join(out_dir, 'file-inventory.json')
    inventory = load_json(inventory_path) if os.path.isfile(inventory_path) else {}

    # Validate JSON schemas
    errors = validate_analysis(analysis) + validate_review(review)
    if errors:
        print('Validation errors:', file=sys.stderr)
        for e in errors:
            print(f'  - {e}', file=sys.stderr)
        sys.exit(1)

    meta = analysis.get('metadata', {})
    today = date.today().strftime('%B %d, %Y').replace(' 0', ' ')

    replacements = {
        '{{SKILL_NAME}}': meta.get('name', analysis.get('skill_name', '')),
        '{{SKILL_DESCRIPTION}}': html.escape(meta.get('description', '')),
        '{{TOTAL_FILES}}': str(analysis.get('total_files', 0)),
        '{{TOTAL_LINES}}': str(analysis.get('total_lines', 0)),
        '{{LICENSE}}': html.escape(meta.get('license') or '\u2014'),
        '{{COMPATIBILITY}}': html.escape(meta.get('compatibility') or '\u2014'),
        '{{GENERATED_DATE}}': today,
        '{{HEADER_SOURCE}}': gen_header_source(analysis),
        '{{SUMMARY_ONELINER}}': gen_summary_oneliner(analysis),
        '{{OVERVIEW_SUMMARY}}': gen_overview_summary(analysis),
        '{{TOOLS_SECTION}}': gen_tools_section(analysis),
        '{{FILE_TREE}}': gen_file_tree(analysis),
        '{{DESIGN_DECISIONS}}': gen_design_decisions(analysis),
        '{{FILE_ANALYSIS_CARDS}}': gen_file_analysis_cards(analysis),
        '{{MERMAID_SEQUENCE}}': sanitize_mermaid_sequence(analysis.get('mermaid_sequence', '')),
        '{{MERMAID_FLOWCHART}}': sanitize_mermaid_flowchart(analysis.get('mermaid_flowchart', '')),
        '{{GRADE_CLASS}}': f'grade-{review.get("grade", "C")}',
        '{{GRADE_LETTER}}': review.get('grade', 'C'),
        '{{GRADE_ASSESSMENT}}': gen_grade_assessment(review),
        '{{GRADE_STRENGTHS}}': gen_grade_strengths(review),
        '{{GRADE_IMPROVEMENTS}}': gen_grade_improvements(review),
        '{{SCORE_BARS}}': gen_score_bars(review),
        '{{EXTERNAL_INTERACTIONS}}': gen_external_interactions(analysis),
        '{{SECRET_ALERTS}}': gen_secret_alerts(inventory),
        '{{FINDINGS}}': gen_findings(review),
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    out_path = os.path.join(out_dir, 'report.html')
    with open(out_path, 'w') as f:
        f.write(result)

    print(out_path)


if __name__ == '__main__':
    main()
