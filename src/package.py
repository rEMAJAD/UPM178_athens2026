"""Create the requested submission ZIP, excluding caches and intermediate artifacts."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    if len(list((ROOT/'data').glob('instance_*.dzn')))<10:
        raise RuntimeError('Submission requires at least ten datasets')
    if not (ROOT/'results/report.pdf').exists():
        raise RuntimeError('Build the report first')
    files=[]
    for folder in ['src','data','results']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ['.pyc', '.zip']
                     and p.name not in ['course_notes.txt'])
    files.extend(ROOT/name for name in ['main.py','settings.py','README.md','requirements.txt'])
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    target=ROOT/'results/upm178_2026_name_surname.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(files): z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('MANIFEST.sha256.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None: raise RuntimeError('Archive integrity verification failed')
    print(f'{target} ({target.stat().st_size:,} bytes, {len(files)} files plus manifest)')


if __name__=='__main__': main()
