from __future__ import annotations
import re
from pathlib import Path

TEXT_SUFFIXES={".py",".js",".ts",".tsx",".jsx",".java",".kt",".kts",".dart",".swift",".go",".rb",".php",".cs",".html",".yaml",".yml",".json",".toml",".env",".sh",".ps1"}
SECRET_PATTERNS=[
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("hardcoded credential", re.compile(r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
]
DANGEROUS=[
    ("shell execution", re.compile(r"(?i)subprocess\.(?:run|Popen|call)\([^\n]*(?:shell\s*=\s*True)")),
    ("unsafe eval", re.compile(r"\beval\s*\(")),
    ("unsafe exec", re.compile(r"\bexec\s*\(")),
    ("disabled TLS verification", re.compile(r"(?i)verify\s*=\s*False")),
]

def changed_texts(root: Path, changed_files: list[str]|None=None):
    paths=[]
    if changed_files:
        paths=[root/p for p in changed_files]
    else:
        paths=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts]
    for p in paths:
        if p.is_file() and (p.suffix.lower() in TEXT_SUFFIXES or p.name in {'Dockerfile','Makefile'}):
            try: yield p.relative_to(root).as_posix(), p.read_text(encoding='utf-8',errors='ignore')
            except OSError: continue

def security_findings(root: Path, changed_files: list[str]|None=None)->list[str]:
    out=[]
    for rel,text in changed_texts(root,changed_files):
        for name,rx in SECRET_PATTERNS + DANGEROUS:
            if rx.search(text): out.append(f"{rel}: {name}")
    return sorted(set(out))

def quality_findings(root: Path, changed_files: list[str]|None=None)->list[str]:
    out=[]
    for rel,text in changed_texts(root,changed_files):
        if re.search(r"(?i)\b(?:TODO|FIXME)\b",text): out.append(f"{rel}: unresolved TODO/FIXME")
        if re.search(r"(?i)(?:pytest\.mark\.skip|unittest\.skip|describe\.skip|it\.skip|test\.skip)",text): out.append(f"{rel}: skipped automated test")
        if len(text.splitlines())>2000: out.append(f"{rel}: unusually large changed file")
    return sorted(set(out))
