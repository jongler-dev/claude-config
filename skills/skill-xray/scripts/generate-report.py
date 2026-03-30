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
        ('Structure', 'structure', None),
        ('Spec Compliance', 'spec_compliance', 'spec'),
        ('Security', 'security', 'security'),
        ('Quality', 'quality', None),
        ('Best Practices', 'best_practices', 'best-practice'),
        ('Overall', 'overall', None),
    ]
    bars = []
    for label, key, source in categories:
        n = scores.get(key, 0)
        color = score_color(n)
        is_overall = key == 'overall'
        cls = 'score-bar score-bar-overall' if is_overall else 'score-bar'
        source_attr = f' data-source="{source}" onclick="clickScoreBar(\'{source}\',this)"' if source else ''
        bars.append(
            f'<div class="{cls}"{source_attr}>'
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
        is_test = h.get('context', 'production') == 'test'
        hit_class = 'secret-hit secret-hit-test' if is_test else 'secret-hit'
        test_label = '<span class="secret-hit-test-label">test file</span>' if is_test else ''
        out += (
            f'<div class="{hit_class}">'
            f'<span class="secret-hit-loc">{html.escape(h["file"])}:{h["line"]}</span>'
            f'<span class="badge secret-cat-{html.escape(cat_class)}">{html.escape(h["label"])}</span>'
            f'<code class="secret-hit-redacted">{html.escape(h["redacted"])}</code>'
            f'{test_label}'
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
# New generators for UX redesign
# ---------------------------------------------------------------------------

COMPOSITION_COLORS = {
    'skill_definition': '#60a5fa',
    'agent_prompt': '#a855f7',
    'script': '#f59e0b',
    'reference': '#22c55e',
    'asset': '#666666',
    'config': '#666666',
    'other': '#666666',
}

COMPOSITION_LABELS = {
    'skill_definition': 'Skill Definition',
    'agent_prompt': 'Agents',
    'script': 'Scripts',
    'reference': 'References',
    'asset': 'Assets',
    'config': 'Config',
    'other': 'Other',
}


def gen_sidebar(analysis, review, inventory):
    """Generate the sidebar HTML: About, Capabilities, Stats, Composition, Score."""
    meta = analysis.get('metadata', {})
    flow = analysis.get('execution_flow', {})
    scores = review.get('scores', {})
    caps = inventory.get('capabilities', {})
    eval_info = inventory.get('eval_info', {})
    file_tree = analysis.get('file_tree', [])

    sections = []

    # About
    trigger = html.escape(flow.get('trigger', ''))
    outputs_list = flow.get('outputs', [])
    outputs_str = html.escape(', '.join(outputs_list) if outputs_list else '')
    license_val = html.escape(meta.get('license') or '\u2014')

    about = '<div class="sidebar-section">'
    about += '<div class="sidebar-section-title">About</div>'
    if trigger:
        about += f'<div class="sidebar-about-trigger">{trigger}</div>'
    if outputs_str:
        about += f'<div class="sidebar-meta-row"><span class="sidebar-meta-icon">&#9654;</span><span>Outputs: {outputs_str}</span></div>'
    about += f'<div class="sidebar-meta-row"><span class="sidebar-meta-icon">&#9881;</span><span>{license_val}</span></div>'
    about += '</div>'
    sections.append(about)

    # Capabilities
    cap_badges = []
    if caps.get('has_shell'):
        label = 'Shell (scoped)' if caps.get('shell_scoped') else 'Shell'
        cap_badges.append(f'<span class="capability-badge capability-badge-shell">{label}</span>')
    if caps.get('has_network'):
        cap_badges.append('<span class="capability-badge capability-badge-network">Network</span>')
    if caps.get('has_fs_write'):
        cap_badges.append('<span class="capability-badge capability-badge-fs-write">FS Write</span>')
    if caps.get('has_mcp'):
        cap_badges.append('<span class="capability-badge capability-badge-mcp">MCP</span>')
    if caps.get('has_agents'):
        cap_badges.append('<span class="capability-badge capability-badge-agents">Agents</span>')

    if cap_badges:
        caps_html = '<div class="sidebar-section">'
        caps_html += '<div class="sidebar-section-title">Capabilities</div>'
        caps_html += f'<div class="capability-badges">{" ".join(cap_badges)}</div>'
        caps_html += '</div>'
        sections.append(caps_html)

    # Stats
    total_files = analysis.get('total_files', 0)
    total_lines = analysis.get('total_lines', 0)
    stats = '<div class="sidebar-section">'
    stats += '<div class="sidebar-section-title">Stats</div>'
    stats += f'<div class="sidebar-stat"><span class="sidebar-meta-icon">&#128196;</span><span><strong>{total_files}</strong> files</span></div>'
    stats += f'<div class="sidebar-stat"><span class="sidebar-meta-icon">#</span><span><strong>{total_lines}</strong> lines</span></div>'
    if eval_info.get('has_evals'):
        count = eval_info.get('eval_count', 0)
        label = f'{count} evals' if count > 0 else 'evals'
        stats += f'<div class="sidebar-stat sidebar-stat-evals"><span class="sidebar-meta-icon" style="color:var(--green)">&#10003;</span><span><strong>{label}</strong></span></div>'
    if eval_info.get('has_test_files'):
        stats += f'<div class="sidebar-stat"><span class="sidebar-meta-icon">&#128295;</span><span>test files</span></div>'
    stats += '</div>'
    sections.append(stats)

    # Composition bar
    type_lines = {}
    for f in file_tree:
        t = f.get('type', 'other')
        type_lines[t] = type_lines.get(t, 0) + f.get('lines', 0)

    total = sum(type_lines.values()) or 1
    if type_lines:
        comp = '<div class="sidebar-section">'
        comp += '<div class="sidebar-section-title">Composition</div>'
        comp += '<div class="composition-bar">'
        for t in ['skill_definition', 'agent_prompt', 'script', 'reference', 'asset', 'config', 'other']:
            lines = type_lines.get(t, 0)
            if lines == 0:
                continue
            pct = (lines / total) * 100
            color = COMPOSITION_COLORS.get(t, '#666')
            label = COMPOSITION_LABELS.get(t, t)
            comp += f'<div style="width:{pct:.1f}%;background:{color}" title="{label} \u2014 {lines} lines"></div>'
        comp += '</div>'
        comp += '<div class="composition-legend">'
        for t in ['skill_definition', 'agent_prompt', 'script', 'reference', 'asset', 'config', 'other']:
            lines = type_lines.get(t, 0)
            if lines == 0:
                continue
            color = COMPOSITION_COLORS.get(t, '#666')
            label = COMPOSITION_LABELS.get(t, t)
            pct = (lines / total) * 100
            comp += f'<div class="composition-legend-item"><span class="composition-dot" style="background:{color}"></span>{label} {pct:.0f}%</div>'
        comp += '</div>'
        comp += '</div>'
        sections.append(comp)

    # Mini score bars
    categories = [
        ('Security', 'security'),
        ('Spec', 'spec_compliance'),
        ('Quality', 'quality'),
        ('Structure', 'structure'),
    ]
    score_html = '<div class="sidebar-section">'
    score_html += '<div class="sidebar-section-title">Confidence Score</div>'
    score_html += f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.6rem">'
    score_html += f'<div class="grade {_grade_class(review)}">{review.get("grade", "C")}</div>'
    score_html += f'<span style="font-size:0.82rem;color:var(--text-secondary)">{scores.get("overall", 0)} / 100</span>'
    score_html += '</div>'
    score_html += '<div class="mini-score-bars">'
    for label, key in categories:
        n = scores.get(key, 0)
        color = score_color(n)
        score_html += f'<div class="mini-score-bar"><label>{label}</label>'
        score_html += f'<div class="mini-score-track"><div class="mini-score-fill" style="width:{n}%;background:{color}"></div></div>'
        score_html += f'<span class="mini-score-value">{n}</span></div>'
    score_html += '</div>'
    score_html += '<a href="#review" class="sidebar-score-link" onclick="switchTab(\'review\', document.querySelectorAll(\'.tab\')[2])">Full review &#8594;</a>'
    score_html += '</div>'
    sections.append(score_html)

    return '\n'.join(sections)


def _grade_class(review):
    return f'grade-{review.get("grade", "C")}'


def gen_steps_table(analysis):
    """Generate the steps table HTML from execution_flow.steps."""
    steps = analysis.get('execution_flow', {}).get('steps', [])
    if not steps:
        return '<p style="color:var(--text-muted);font-size:0.85rem">No execution steps available.</p>'

    rows = []
    for s in steps:
        step_num = s.get('step', '')
        action = html.escape(s.get('action', ''))
        tools = s.get('tools', [])
        conditional = s.get('conditional', False)
        condition = html.escape(s.get('condition', ''))

        tool_badges = ' '.join(
            f'<span class="badge tool">{html.escape(t)}</span>' for t in tools
        ) if tools else '<span style="color:var(--text-muted)">\u2014</span>'

        cond_html = f'<span class="step-condition">{condition}</span>' if conditional and condition else '<span style="color:var(--text-muted)">\u2014</span>'

        action_lower = action.lower()
        is_approval = any(kw in action_lower for kw in ['user confirm', 'user approv', 'user review', 'ask user', 'wait for user', 'user validates'])
        row_class = ' class="approval-step"' if is_approval else ''
        dot = '<span class="approval-dot"></span>' if is_approval else ''

        rows.append(
            f'<tr{row_class}>'
            f'<td class="step-num">{step_num}</td>'
            f'<td>{dot}{action}</td>'
            f'<td>{tool_badges}</td>'
            f'<td>{cond_html}</td>'
            f'</tr>'
        )

    return (
        '<div class="card"><div style="overflow-x:auto">'
        '<table class="steps-table">'
        '<thead><tr><th>#</th><th>Action</th><th>Tools</th><th>Condition</th></tr></thead>'
        '<tbody>' + '\n'.join(rows) + '</tbody>'
        '</table></div></div>'
    )


def gen_error_handling(analysis):
    """Generate error handling callout."""
    eh = analysis.get('execution_flow', {}).get('error_handling', '')
    if not eh or eh.lower() == 'none':
        return ''
    return (
        f'<div class="callout-bar">'
        f'<span class="callout-label">Error Handling</span>'
        f'<span class="callout-value">{html.escape(eh)}</span>'
        f'</div>'
    )


def gen_outputs(analysis):
    """Generate outputs callout."""
    outputs = analysis.get('execution_flow', {}).get('outputs', [])
    if not outputs:
        return ''
    text = html.escape(', '.join(outputs))
    return (
        f'<div class="callout-bar">'
        f'<span class="callout-label">Outputs</span>'
        f'<span class="callout-value">{text}</span>'
        f'</div>'
    )


def gen_spec_matrix(review):
    """Generate the spec compliance chip matrix."""
    rules = review.get('spec_compliance', [])
    if not rules:
        return '<p style="color:var(--text-muted);font-size:0.85rem">No spec compliance data.</p>'

    applicable = [r for r in rules if r.get('status', '').lower() != 'n/a']
    passed = sum(1 for r in applicable if r.get('status', '').lower() == 'pass')
    total_applicable = len(applicable)

    summary = f'<div class="spec-matrix-summary">{passed} of {total_applicable} rules passed</div>'

    fails = [r for r in rules if r.get('status', '').lower() in ('fail',)]
    warns = [r for r in rules if r.get('status', '').lower() in ('warn', 'warning')]
    passes = [r for r in rules if r.get('status', '').lower() == 'pass']
    nas = [r for r in rules if r.get('status', '').lower() == 'n/a']

    chips = []
    icons = {'fail': '&#10007;', 'warn': '&#9888;', 'pass': '&#10003;', 'n/a': '&#8212;'}

    for r in fails:
        rule = html.escape(r.get('rule', ''))
        detail = html.escape(r.get('detail', ''))
        chips.append(f'<span class="spec-chip spec-chip-fail" title="{detail}">{icons["fail"]} {rule}</span>')

    for r in warns:
        rule = html.escape(r.get('rule', ''))
        detail = html.escape(r.get('detail', ''))
        chips.append(f'<span class="spec-chip spec-chip-warn" title="{detail}">{icons["warn"]} {rule}</span>')

    max_pass_shown = 10 if len(passes) > 15 else len(passes)
    for r in passes[:max_pass_shown]:
        rule = html.escape(r.get('rule', ''))
        detail = html.escape(r.get('detail', ''))
        chips.append(f'<span class="spec-chip spec-chip-pass" title="{detail}">{icons["pass"]} {rule}</span>')
    if len(passes) > max_pass_shown:
        remaining = len(passes) - max_pass_shown
        chips.append(f'<span class="spec-matrix-overflow">+{remaining} more passed</span>')

    for r in nas:
        rule = html.escape(r.get('rule', ''))
        detail = html.escape(r.get('detail', ''))
        chips.append(f'<span class="spec-chip spec-chip-na" title="{detail}">{icons["n/a"]} {rule}</span>')

    return summary + '<div class="spec-matrix">' + '\n'.join(chips) + '</div>'


def gen_finding_filters(review):
    """Generate the finding filter bar HTML with counts."""
    findings_data = []
    _collect_finding_counts(findings_data, review.get('spec_compliance', []), 'spec', status_mode=True)
    _collect_finding_counts(findings_data, review.get('security_findings', []), 'security')
    _collect_finding_counts(findings_data, review.get('best_practices', []), 'best-practice')
    _collect_finding_counts(findings_data, review.get('judgment_findings', []), 'judgment')

    errors = sum(1 for f in findings_data if f['severity'] == 'error')
    warnings = sum(1 for f in findings_data if f['severity'] == 'warning')
    total = errors + warnings

    by_source = {}
    for f in findings_data:
        by_source[f['source']] = by_source.get(f['source'], 0) + 1

    out = '<div class="finding-filters">'

    out += '<span class="finding-filter-label">Severity</span>'
    out += f'<button class="finding-filter-btn active" data-axis="severity" data-value="all" onclick="filterFindings(\'severity\',\'all\',this)">All <span class="finding-filter-count">{total}</span></button>'
    if errors:
        out += f'<button class="finding-filter-btn" data-axis="severity" data-value="error" onclick="filterFindings(\'severity\',\'error\',this)">Errors <span class="finding-filter-count" style="color:var(--red)">{errors}</span></button>'
    if warnings:
        out += f'<button class="finding-filter-btn" data-axis="severity" data-value="warning" onclick="filterFindings(\'severity\',\'warning\',this)">Warnings <span class="finding-filter-count" style="color:var(--yellow)">{warnings}</span></button>'

    out += '<span class="finding-filter-sep">|</span>'

    out += '<span class="finding-filter-label">Source</span>'
    source_labels = {'spec': 'Spec', 'security': 'Security', 'best-practice': 'Best Practice', 'judgment': 'Judgment'}
    for src, label in source_labels.items():
        count = by_source.get(src, 0)
        if count:
            out += f'<button class="finding-filter-btn" data-axis="source" data-value="{src}" onclick="filterFindings(\'source\',\'{src}\',this)">{label} <span class="finding-filter-count">{count}</span></button>'

    out += '</div>'
    return out


def _collect_finding_counts(findings, items, source, status_mode=False):
    """Collect findings for counting (mirrors _add_findings logic but without dedup)."""
    for item in items:
        if status_mode:
            status = item.get('status', '').lower()
            if status in ('pass', 'n/a'):
                continue
            sev = normalize_severity(status)
        else:
            sev = normalize_severity(item.get('severity', 'info'))
            if sev == 'info':
                continue
        findings.append({'severity': sev, 'source': source})


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
        '{{SIDEBAR}}': gen_sidebar(analysis, review, inventory),
        '{{DESIGN_DECISIONS}}': gen_design_decisions(analysis),
        '{{FILE_ANALYSIS_CARDS}}': gen_file_analysis_cards(analysis),
        '{{STEPS_TABLE}}': gen_steps_table(analysis),
        '{{ERROR_HANDLING}}': gen_error_handling(analysis),
        '{{OUTPUTS}}': gen_outputs(analysis),
        '{{MERMAID_SEQUENCE}}': sanitize_mermaid_sequence(analysis.get('mermaid_sequence', '')),
        '{{MERMAID_FLOWCHART}}': sanitize_mermaid_flowchart(analysis.get('mermaid_flowchart', '')),
        '{{GRADE_CLASS}}': _grade_class(review),
        '{{GRADE_LETTER}}': review.get('grade', 'C'),
        '{{GRADE_ASSESSMENT}}': gen_grade_assessment(review),
        '{{GRADE_STRENGTHS}}': gen_grade_strengths(review),
        '{{GRADE_IMPROVEMENTS}}': gen_grade_improvements(review),
        '{{SCORE_BARS}}': gen_score_bars(review),
        '{{SPEC_MATRIX}}': gen_spec_matrix(review),
        '{{FINDING_FILTERS}}': gen_finding_filters(review),
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
