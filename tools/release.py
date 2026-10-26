"""Сборка релиза YartMods: все моды репозитория -> dist/YartMods.zip, по запросу — релиз на GitHub.

    python tools/release.py                                     # srmod build каждого мода -> dist/YartMods.zip
    python tools/release.py --publish v1.0.0 --notes notes.md   # то же + gh release create

Мод — папка верхнего уровня с srmod.json; его build/ ложится в архив под путь "install" из
srmod.json (Mods/Artem/TowBeam/...). Кроме Mods/... в архиве ничего нет: агрегатор модов принимает
файлы вне Mods/ за файлы движка. Имя архива одно во всех релизах, поэтому
https://github.com/ArtYudin89/YartMods/releases/latest/download/YartMods.zip всегда даёт последнюю
сборку — по этой ссылке моды берёт агрегатор.

Сборщик — sr-modkit рядом с клоном YartMods (..\\sr-modkit), ему нужен rsmc (см. README sr-modkit).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODKIT = os.path.join(os.path.dirname(ROOT), 'sr-modkit')  # next to the YartMods clone
ARCHIVE = os.path.join(ROOT, 'dist', 'YartMods.zip')
REPO = 'ArtYudin89/YartMods'


def find_mods():
    """[(папка, путь установки)] всех модов репозитория."""
    out = []
    for name in sorted(os.listdir(ROOT)):
        cfg = os.path.join(ROOT, name, 'srmod.json')
        if os.path.isfile(cfg):
            with open(cfg, encoding='utf-8') as f:
                install = json.load(f)['install'].strip('/')
            if not install.startswith('Mods/'):
                sys.exit(f'{name}/srmod.json: install "{install}" не в Mods/')
            out.append((name, install))
    if not out:
        sys.exit('модов (папок с srmod.json) нет')
    return out


def build(name):
    env = dict(os.environ, PYTHONPATH=MODKIT)
    subprocess.run([sys.executable, '-X', 'utf8', '-m', 'srmod', 'build', os.path.join(ROOT, name)],
                   env=env, check=True)


def pack(mods):
    """build/ каждого мода -> ARCHIVE под его путь установки; даты файлов сохраняются."""
    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    entries = []
    with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, install in mods:
            build_dir = os.path.join(ROOT, name, 'build')
            for dirpath, dirnames, filenames in os.walk(build_dir):
                dirnames.sort()
                for fn in sorted(filenames):
                    src = os.path.join(dirpath, fn)
                    arc = install + '/' + os.path.relpath(src, build_dir).replace(os.sep, '/')
                    z.write(src, arc)
                    entries.append((arc, os.path.getsize(src)))
    return entries


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def publish(tag, notes):
    """Релиз tag на текущем коммите; коммит должен быть чистым и уже лежать в origin/master."""
    if git('status', '--porcelain'):
        sys.exit('в рабочей копии есть незакоммиченное — релиз собирается только с коммита')
    head = git('rev-parse', 'HEAD')
    git('fetch', '-q', 'origin')
    if subprocess.run(['git', 'merge-base', '--is-ancestor', head, 'origin/master'],
                      cwd=ROOT).returncode:
        sys.exit('коммит ещё не в origin/master — сначала git push')
    subprocess.run(['gh', 'release', 'create', tag, ARCHIVE, '--repo', REPO, '--target', head,
                    '--title', f'YartMods {tag}', '--notes-file', notes, '--latest'], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--publish', metavar='TAG', help='выложить архив релизом TAG (vX.Y.Z)')
    ap.add_argument('--notes', help='файл с текстом релиза (нужен с --publish)')
    a = ap.parse_args()
    if a.publish and not a.notes:
        ap.error('--publish требует --notes')

    mods = find_mods()
    for name, _ in mods:
        build(name)
    entries = pack(mods)
    with open(ARCHIVE, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    for arc, size in entries:
        print(f'  {size:>8}  {arc}')
    print(f'{os.path.relpath(ARCHIVE, ROOT)}: {len(entries)} файлов, '
          f'{os.path.getsize(ARCHIVE)} байт, sha256 {digest}')
    if a.publish:
        publish(a.publish, a.notes)


if __name__ == '__main__':
    main()
