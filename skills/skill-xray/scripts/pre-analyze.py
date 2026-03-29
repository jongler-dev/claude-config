#!/usr/bin/env python3
"""Deterministic pre-analysis of a skill directory.

Produces file-inventory.json with file tree, frontmatter, line counts,
and structural spec checks — all data that needs zero LLM reasoning.

Usage: pre-analyze.py <skill-dir> <output-path>
"""

import fnmatch
import json
import math
import os
import re
import sys


# ---------------------------------------------------------------------------
# Secret scanning — categorized detector registry with entropy analysis
# ---------------------------------------------------------------------------

def _shannon_entropy(s):
    """Calculate Shannon entropy of a string (bits per character)."""
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def _redact(value, show_prefix=4, show_suffix=2):
    """Redact a secret value, preserving a short prefix and suffix."""
    value = value.strip().strip('"').strip("'")
    if len(value) <= show_prefix + show_suffix + 3:
        return '*' * len(value)
    return value[:show_prefix] + '***' + value[-show_suffix:]


# Each detector: id, category, label, pattern (with a 'secret' named group for the sensitive part)
_DETECTORS = [
    # -- Cloud provider keys --
    {
        'id': 'aws-access-key',
        'category': 'cloud',
        'label': 'AWS Access Key ID',
        'pattern': re.compile(r'(?P<secret>AKIA[0-9A-Z]{16})'),
    },
    {
        'id': 'aws-secret-key',
        'category': 'cloud',
        'label': 'AWS Secret Access Key',
        'pattern': re.compile(r'(?:aws_secret_access_key|secret_key)\s*[=:]\s*["\']?(?P<secret>[A-Za-z0-9/+=]{40})["\']?', re.IGNORECASE),
    },
    {
        'id': 'gcp-service-account',
        'category': 'cloud',
        'label': 'GCP Service Account Key',
        'pattern': re.compile(r'"type"\s*:\s*"service_account"'),
    },
    {
        'id': 'azure-connection-string',
        'category': 'cloud',
        'label': 'Azure Connection String',
        'pattern': re.compile(r'(?P<secret>DefaultEndpointsProtocol=https?;AccountName=[^;]+;AccountKey=[^;]+)'),
    },
    # -- Platform tokens --
    {
        'id': 'github-token',
        'category': 'platform',
        'label': 'GitHub Token',
        'pattern': re.compile(r'(?P<secret>(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255})'),
    },
    {
        'id': 'gitlab-token',
        'category': 'platform',
        'label': 'GitLab Token',
        'pattern': re.compile(r'(?P<secret>glpat-[A-Za-z0-9_-]{20,})'),
    },
    {
        'id': 'slack-token',
        'category': 'platform',
        'label': 'Slack Token',
        'pattern': re.compile(r'(?P<secret>xox[bporas]-[A-Za-z0-9-]+)'),
    },
    {
        'id': 'npm-token',
        'category': 'platform',
        'label': 'npm Token',
        'pattern': re.compile(r'(?P<secret>npm_[A-Za-z0-9]{36,})'),
    },
    {
        'id': 'pypi-token',
        'category': 'platform',
        'label': 'PyPI Token',
        'pattern': re.compile(r'(?P<secret>pypi-[A-Za-z0-9_-]{50,})'),
    },
    {
        'id': 'stripe-key',
        'category': 'platform',
        'label': 'Stripe API Key',
        'pattern': re.compile(r'(?P<secret>(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{24,})'),
    },
    # -- AI provider keys --
    {
        'id': 'anthropic-key',
        'category': 'platform',
        'label': 'Anthropic API Key',
        'pattern': re.compile(r'(?P<secret>sk-ant-[A-Za-z0-9_-]{32,})'),
    },
    {
        'id': 'openai-key',
        'category': 'platform',
        'label': 'OpenAI API Key',
        'pattern': re.compile(r'(?P<secret>sk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{32,})'),
    },
    {
        'id': 'gemini-key',
        'category': 'platform',
        'label': 'Google Gemini API Key',
        'pattern': re.compile(r'(?P<secret>AIzaSy[A-Za-z0-9_-]{33})'),
    },
    # -- Cryptographic material --
    {
        'id': 'private-key',
        'category': 'crypto',
        'label': 'Private Key',
        'pattern': re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
    },
    {
        'id': 'jwt-token',
        'category': 'crypto',
        'label': 'JWT Token',
        'pattern': re.compile(r'(?P<secret>eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+)'),
    },
    # -- Connection strings --
    {
        'id': 'database-url',
        'category': 'connection',
        'label': 'Database URL with Credentials',
        'pattern': re.compile(r'(?P<secret>(?:postgres|mysql|mongodb|redis|amqp)(?:ql)?://[^:]+:[^@]+@[^\s"\']+)'),
    },
    # -- Generic assignment patterns --
    {
        'id': 'generic-secret-assignment',
        'category': 'generic',
        'label': 'Hardcoded Secret in Assignment',
        'pattern': re.compile(
            r'(?:password|passwd|secret|api_key|apikey|api-key|token|auth_token|access_token)'
            r'\s*[=:]\s*["\'](?P<secret>[^"\']{8,})["\']',
            re.IGNORECASE,
        ),
    },
]

# Entropy threshold for the generic detector — low-entropy values like
# "changeme" or "password123" are intentional placeholders, not real secrets
_GENERIC_ENTROPY_THRESHOLD = 3.5

# Standalone high-entropy catch-all: long hex/base64 strings in assignments
_HIGH_ENTROPY_PATTERN = re.compile(
    r'[=:]\s*["\'](?P<secret>[A-Za-z0-9+/=_-]{32,})["\']'
)
_HIGH_ENTROPY_THRESHOLD = 4.5


def scan_secrets(skill_dir, file_tree):
    """Scan all text files for potential secrets. Returns list of hit dicts."""
    hits = []

    for entry in file_tree:
        relpath = entry['path']
        fpath = os.path.join(skill_dir, relpath)

        # Skip binary/asset files
        if entry.get('type') == 'asset':
            continue
        if relpath.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')):
            continue

        try:
            with open(fpath, 'r', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            continue

        for line_num, line in enumerate(lines, start=1):
            # Run every detector against this line
            for det in _DETECTORS:
                m = det['pattern'].search(line)
                if not m:
                    continue

                secret_val = m.group('secret') if 'secret' in m.groupdict() else m.group(0)

                # For generic assignments, skip low-entropy values (placeholders)
                if det['id'] == 'generic-secret-assignment':
                    if _shannon_entropy(secret_val) < _GENERIC_ENTROPY_THRESHOLD:
                        continue

                hits.append({
                    'file': relpath,
                    'line': line_num,
                    'detector': det['id'],
                    'category': det['category'],
                    'label': det['label'],
                    'redacted': _redact(secret_val),
                })

            # High-entropy catch-all (only fires if no named detector already matched this line)
            if not any(h['file'] == relpath and h['line'] == line_num for h in hits):
                for m in _HIGH_ENTROPY_PATTERN.finditer(line):
                    val = m.group('secret')
                    if _shannon_entropy(val) >= _HIGH_ENTROPY_THRESHOLD:
                        hits.append({
                            'file': relpath,
                            'line': line_num,
                            'detector': 'high-entropy-string',
                            'category': 'entropy',
                            'label': 'High-Entropy String',
                            'redacted': _redact(val),
                        })

    return hits


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text):
    """Extract YAML-like frontmatter from SKILL.md content."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}, text

    raw = m.group(1)
    body = text[m.end():]
    fm = {}

    # Simple YAML parser for flat/shallow structure (no nested objects beyond metadata)
    current_key = None
    current_value_lines = []

    def flush():
        if current_key:
            val = '\n'.join(current_value_lines).strip()
            # Strip quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            fm[current_key] = val

    for line in raw.split('\n'):
        # Key-value pair
        kv = re.match(r'^(\w[\w-]*):\s*(.*)', line)
        if kv and not line.startswith(' ') and not line.startswith('\t'):
            flush()
            current_key = kv.group(1)
            current_value_lines = [kv.group(2)]
        elif current_key and (line.startswith('  ') or line.startswith('\t')):
            current_value_lines.append(line.strip())
        elif line.strip() == '' and current_key:
            current_value_lines.append('')
    flush()

    # Parse allowed-tools as list
    allowed_tools_raw = fm.get('allowed-tools', '')
    allowed_tools = [t.strip() for t in allowed_tools_raw.split() if t.strip()]

    # Parse metadata block (simple key: value pairs indented under metadata:)
    metadata = {}
    in_metadata = False
    for line in raw.split('\n'):
        if re.match(r'^metadata:\s*$', line):
            in_metadata = True
            continue
        if in_metadata:
            mm = re.match(r'^  (\w[\w-]*):\s*(.*)', line)
            if mm:
                val = mm.group(2).strip().strip('"').strip("'")
                metadata[mm.group(1)] = val
            elif not line.startswith(' ') and not line.startswith('\t') and line.strip():
                in_metadata = False

    # Clean up YAML block scalar indicators (>, |) from values
    for key in fm:
        val = fm[key]
        if isinstance(val, str) and val.startswith(('>', '|')):
            val = val[1:].strip()
            # Collapse folded scalar (>) — join lines with spaces
            val = re.sub(r'\n(?!\n)', ' ', val)
            fm[key] = val

    return {
        'name': fm.get('name', ''),
        'description': fm.get('description', ''),
        'license': fm.get('license', ''),
        'compatibility': fm.get('compatibility', ''),
        'allowed_tools': allowed_tools,
        'metadata': metadata,
    }, body


def classify_file(relpath):
    """Classify a file by its location in the skill directory."""
    if relpath == 'SKILL.md':
        return 'skill_definition'
    parts = relpath.split('/')
    if parts[0] == 'scripts':
        return 'script'
    if parts[0] == 'references':
        return 'reference'
    if parts[0] == 'assets':
        return 'asset'
    if parts[0] == 'agents':
        return 'agent_prompt'
    if parts[0] == '.claude':
        return 'config'
    return 'other'


def count_lines(filepath):
    """Count lines in a file, returning 0 for binary files."""
    try:
        with open(filepath, 'r', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def structural_spec_checks(skill_dir, frontmatter, skill_md_lines, dir_name):
    """Run deterministic spec compliance checks."""
    name = frontmatter.get('name', '')
    desc = frontmatter.get('description', '')

    checks = {}

    # Structure
    checks['has_skill_md'] = os.path.isfile(os.path.join(skill_dir, 'SKILL.md'))
    checks['dir_name_matches_name'] = dir_name == name
    checks['has_scripts_dir'] = os.path.isdir(os.path.join(skill_dir, 'scripts'))
    checks['has_references_dir'] = os.path.isdir(os.path.join(skill_dir, 'references'))
    checks['has_assets_dir'] = os.path.isdir(os.path.join(skill_dir, 'assets'))

    # Name field
    checks['name_present'] = len(name) > 0
    checks['name_length'] = len(name)
    checks['name_length_ok'] = 1 <= len(name) <= 64
    checks['name_charset_ok'] = bool(re.match(r'^[a-z0-9-]+$', name)) if name else False
    checks['name_no_leading_trailing_hyphen'] = (
        not name.startswith('-') and not name.endswith('-')
    ) if name else False
    checks['name_no_consecutive_hyphens'] = '--' not in name if name else False

    # Description field
    checks['description_present'] = len(desc) > 0
    checks['description_length'] = len(desc)
    checks['description_length_ok'] = 1 <= len(desc) <= 1024

    # Body
    checks['skill_md_lines'] = skill_md_lines
    checks['skill_md_under_500_lines'] = skill_md_lines < 500

    # Allowed-tools
    checks['has_allowed_tools'] = len(frontmatter.get('allowed_tools', [])) > 0

    return checks


def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <skill-dir> <output-path>', file=sys.stderr)
        sys.exit(1)

    skill_dir = os.path.abspath(sys.argv[1])
    output_path = sys.argv[2]

    if not os.path.isdir(skill_dir):
        print(f'Error: {skill_dir} is not a directory', file=sys.stderr)
        sys.exit(1)

    skill_md_path = os.path.join(skill_dir, 'SKILL.md')
    if not os.path.isfile(skill_md_path):
        print(f'Error: no SKILL.md found in {skill_dir}', file=sys.stderr)
        sys.exit(1)

    dir_name = os.path.basename(skill_dir)

    # Read and parse SKILL.md
    with open(skill_md_path, 'r') as f:
        skill_md_content = f.read()

    frontmatter, body = parse_frontmatter(skill_md_content)
    skill_md_lines = skill_md_content.count('\n') + 1

    # Parse .gitignore patterns
    gitignore_patterns = []
    gitignore_path = os.path.join(skill_dir, '.gitignore')
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    gitignore_patterns.append(line)

    def is_gitignored(relpath):
        for pattern in gitignore_patterns:
            pat = pattern.rstrip('/')
            # Directory pattern (trailing slash) — match against any path component
            if pattern.endswith('/'):
                if relpath.startswith(pat + '/') or ('/' + pat + '/') in ('/' + relpath):
                    return True
            # File/glob pattern
            if fnmatch.fnmatch(relpath, pat) or fnmatch.fnmatch(os.path.basename(relpath), pat):
                return True
        return False

    # Walk the directory tree
    file_tree = []
    total_lines = 0
    total_files = 0

    for root, dirs, files in os.walk(skill_dir):
        # Skip hidden directories and gitignored directories
        dirs[:] = [d for d in dirs if not d.startswith('.')
                   and not is_gitignored(os.path.relpath(os.path.join(root, d), skill_dir))]
        for fname in sorted(files):
            if fname.startswith('.'):
                continue
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, skill_dir)
            if is_gitignored(relpath):
                continue
            size = os.path.getsize(fpath)
            lines = count_lines(fpath)
            total_lines += lines
            total_files += 1
            file_tree.append({
                'path': relpath,
                'size_bytes': size,
                'lines': lines,
                'type': classify_file(relpath),
            })

    # Sort: SKILL.md first, then alphabetically
    file_tree.sort(key=lambda f: (0 if f['path'] == 'SKILL.md' else 1, f['path']))

    # Structural checks
    checks = structural_spec_checks(skill_dir, frontmatter, skill_md_lines, dir_name)

    # Secret scanning
    secret_hits = scan_secrets(skill_dir, file_tree)

    result = {
        'file_tree': file_tree,
        'total_lines': total_lines,
        'total_files': total_files,
        'frontmatter': frontmatter,
        'skill_md_body': body,
        'structural_spec_checks': checks,
        'secret_scan': {
            'clean': len(secret_hits) == 0,
            'hit_count': len(secret_hits),
            'hits': secret_hits,
        },
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(output_path)


if __name__ == '__main__':
    main()
