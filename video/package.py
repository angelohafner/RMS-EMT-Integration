"""Package editable sources, real display assets and the audited movie."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / 'video/output'
    output.mkdir(exist_ok=True)
    archive = output / 'RMS_EMT_Manim_Editable.zip'
    audit = json.loads((ROOT / 'video/audit.json').read_text(encoding='utf8'))
    movie = output / 'RMS_EMT_Integration_EN_1080p.mp4'
    if not audit['passed'] or digest(movie) != audit['video_sha256']:
        raise ValueError('Movie does not match the released passing audit.')
    files = [ROOT / name for name in [
        'README.md', 'CONTEXT.md', '.gitignore', '.gitattributes', 'pyproject.toml',
        'requirements-tested.txt', 'delivery/RMS_EMT_STATCOM_Dynamic_v2_MANIFEST.json']]
    for folder in ['src', 'tests', 'config', 'templates', 'docs']:
        files.extend(p for p in (ROOT / folder).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts
                     and '.egg-info' not in str(p) and p.suffix != '.pyc')
    for name in ['check_timestep.py', 'check_rms_timestep.py',
                 'export_psse_channels.py', 'package_delivery.py']:
        files.append(ROOT / 'tools' / name)
    for path in (ROOT / 'video').iterdir():
        if path.is_file() and path.suffix in {'.py', '.md', '.json', '.srt', '.txt', '.ps1'}:
            files.append(path)
    for folder in ['assets', 'audio']:
        files.extend(p for p in (ROOT / 'video' / folder).rglob('*') if p.is_file())
    files.append(movie)
    manifest = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(set(files))}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for name in manifest:
            zipped.write(ROOT / name, 'RMS_EMT_Integration/' + name)
        zipped.writestr('RMS_EMT_Integration/EDITABLE_MANIFEST.json',
                        json.dumps({'files': manifest}, indent=2))
    with zipfile.ZipFile(archive) as zipped:
        bad = zipped.testzip()
        if bad:
            raise ValueError('ZIP CRC failure: ' + bad)
        for name, expected in manifest.items():
            actual = hashlib.sha256(zipped.read('RMS_EMT_Integration/' + name)).hexdigest()
            if actual != expected:
                raise ValueError('ZIP hash mismatch: ' + name)
    result = {'archive': archive.name, 'files': len(manifest) + 1,
              'bytes': archive.stat().st_size, 'sha256': digest(archive),
              'crc_and_all_file_hashes_verified': True}
    (output / 'editable_package_audit.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
