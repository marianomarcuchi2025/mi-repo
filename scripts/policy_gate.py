#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
EXEMPT=("tests/","scripts/","docs/")
def ex(p): return any(p.startswith(x) for x in EXEMPT)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bandit",type=Path,default=Path("bandit.json"))
    ap.add_argument("--pip-audit",type=Path,default=Path("pip-audit.json"))
    ap.add_argument("--semgrep",type=Path,default=Path("semgrep.json"))
    ap.add_argument("--summary",type=Path)
    a=ap.parse_args(); b=[]; w=[]
    if a.bandit.exists():
        for f in json.loads(a.bandit.read_text()).get("results",[]):
            s=f.get("issue_severity","LOW").upper(); fp=f.get("filename","")
            v=f"[bandit] {fp}:{f.get('line_number',0)} {f.get('issue_text','')[:120]}"
            (b if s=="HIGH" and not ex(fp) else w).append(v)
    if a.pip_audit.exists():
        for d in json.loads(a.pip_audit.read_text()).get("dependencies",[]):
            for v in d.get("vulns",[]):
                fx=v.get("fix_versions") or []
                m=f"[pip-audit] {d['name']}=={d['version']} {v['id']}"
                (w if not fx else b).append(m)
    if a.semgrep.exists():
        for f in json.loads(a.semgrep.read_text()).get("results",[]):
            s=(f.get("extra",{}).get("severity") or "INFO").upper(); fp=f.get("path","")
            v=f"[semgrep] {fp}:{f.get('start',{}).get('line',0)} {f.get('check_id','')}"
            (b if s=="ERROR" and not ex(fp) else w).append(v)
    for v in b: print(f"BLOQUEA: {v}")
    for v in w: print(f"AVISO:   {v}")
    print(f"\nBLOCK: {len(b)}  ADVISORY: {len(w)}")
    sys.exit(1 if b else 0)
if __name__=="__main__": main()
