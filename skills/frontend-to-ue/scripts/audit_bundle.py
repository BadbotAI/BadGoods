#!/usr/bin/env python3
"""Scan exported UE files and validate canonical screen references; no sensitive values printed."""
import argparse, json, re, sys, zipfile
from pathlib import Path

PATTERNS = {
    'absoluteLocalPath': r'/Users/|/home/|[A-Za-z]:\\Users\\',
    'credential': r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{12,})',
    'email': r'[A-Z0-9._%+-]+@(?!example\.invalid\b)[A-Z0-9.-]+\.[A-Z]{2,}',
    'signedAccessURL': r'https?://[^\s"<>]*(?:X-Amz-Signature|access_token|api_key|token=)',
}
TEXT_EXTENSIONS = {'.html', '.json', '.svg', '.txt', '.md', '.csv', '.css'}

DENY_TERMS = []
def scan_text(label, text):
    found = [{'file': label, 'category': k, 'count': len(matches)}
             for k, p in PATTERNS.items() if (matches := re.findall(p, text, re.I))]
    count = sum(text.casefold().count(term.casefold()) for term in DENY_TERMS if term)
    if count:
        found.append({'file': label, 'category': 'userSpecifiedForbiddenTerm', 'count': count})
    return found

def audit(root):
    findings = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        label = str(path.relative_to(root))
        if path.suffix.lower() in TEXT_EXTENSIONS:
            findings.extend(scan_text(label, path.read_text(encoding='utf-8', errors='replace')))
        elif path.suffix.lower() == '.zip':
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if Path(name).suffix.lower() in TEXT_EXTENSIONS:
                        findings.extend(scan_text(label+'!'+name, z.read(name).decode('utf-8', errors='replace')))
    model = root / 'ue-spec.json'
    checks = {}
    if model.exists():
        data = json.loads(model.read_text(encoding='utf-8'))
        ids = [s['id'] for s in data['screens']]
        dangling = [t['id'] for t in data.get('transitions', []) if t['from'] not in ids or t['to'] not in ids]
        coverage = data.get('coverage', {})
        checks = {
            'screenCount': len(ids), 'uniqueScreenIds': len(ids) == len(set(ids)),
            'danglingTransitions': dangling,
            'requiredScreensPresent': all(i in ids for i in coverage.get('requiredScreenIds', [])),
            'capturesExist': all((root / s['capture']).exists() for s in data['screens'] if s.get('capture')),
        }
    passed = not findings and checks.get('uniqueScreenIds', True) and not checks.get('danglingTransitions') and checks.get('requiredScreensPresent', True) and checks.get('capturesExist', True)
    return {'status': 'pass' if passed else 'fail', 'privacyFindings': findings, 'modelChecks': checks,
            'limitations': ['Pattern scan does not inspect raster image text or prove absence of confidential data.', 'Manual visual review, Figma readback and runtime tests are required separately.']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--deny-file', type=Path, help='Local JSON array of forbidden terms; never copied into the report.')
    args = parser.parse_args()
    if args.deny_file:
        DENY_TERMS[:] = json.loads(args.deny_file.read_text(encoding='utf-8'))
    report = audit(args.directory)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text, encoding='utf-8')
    print(text)
    sys.exit(0 if report['status'] == 'pass' else 1)
