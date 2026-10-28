#!/usr/bin/env python3
"""Local, read-only preflight. Never executes input or prints sensitive matches."""
import argparse, hashlib, json, re
from pathlib import Path

def inspect(path):
    raw = path.read_bytes()
    text = raw.decode('utf-8', errors='replace')
    return {
        'source': {'label': 'frontend-source', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)},
        'structure': {
            'scriptTags': len(re.findall(r'<script\b', text, re.I)),
            'functionDefinitions': len(re.findall(r'function\s+[\w$]+\s*\(', text)),
            'inlineHandlers': len(re.findall(r'\bon(?:click|change|input|submit)\s*=', text, re.I)),
            'storageMentions': len(re.findall(r'\b(?:localStorage|sessionStorage)\b', text)),
            'networkAPIMentions': len(re.findall(r'\b(?:fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon)', text)),
            'externalResourceTags': len(re.findall(r'<(?:script|img|link)\b[^>]*(?:src|href)=["\x27]https?://', text, re.I)),
        },
        'reviewCounts': {
            'absoluteLocalPaths': len(re.findall(r'/Users/|/home/|[A-Za-z]:\\Users\\', text)),
            'emailLikeStrings': len(re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text)),
            'credentialLikeStrings': len(re.findall(r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{12,})', text)),
        },
        'limitations': ['Counts are signals, not proof of reachability, safety, or completeness.', 'Run only in an isolated browser after review.'],
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = json.dumps(inspect(args.input), ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding='utf-8')
    else:
        print(result)
