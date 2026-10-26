"""Вариант отладочной сборки с другими настройками TowBeam.Cfg (например, эффект луча):
build-debug/ -> .window/variants/<имя>/ с правкой параметров в обоих Lang.dat.

Запуск из корня проекта после python tools/make_debug.py:
    python tools/make_variant.py <имя> Параметр=Значение [Параметр=Значение ...]
    python tools/make_variant.py beam_D2 BeamEffect=Weapon.10 BeamPalette=2
Папку варианта передать четвёртым аргументом tools/window_session.py.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = os.path.join(os.path.dirname(os.path.dirname(ROOT)), 'sr-lab', 'sr.py')  # next to the YartMods clone
SRC = os.path.join(ROOT, 'build-debug')
OUT = os.path.join(ROOT, '.window', 'variants')


def sr(*args):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    subprocess.run([sys.executable, SR] + list(args), check=True, env=env, stdout=subprocess.DEVNULL)


def apply(entries, changes, path=()):
    """Поставить значения параметрам TowBeam/Cfg; вернуть имена найденных."""
    done = set()
    for entry in entries:
        if entry.get('kind') == 'block':
            done |= apply(entry.get('entries', []), changes, path + (entry.get('name'),))
        elif entry.get('kind') == 'param' and path == ('TowBeam', 'Cfg') and entry.get('name') in changes:
            entry['value'] = changes[entry['name']]
            done.add(entry['name'])
    return done


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    name = sys.argv[1]
    changes = dict(item.split('=', 1) for item in sys.argv[2:])
    if not os.path.isdir(SRC):
        sys.exit('нет build-debug/ — сначала python tools/make_debug.py')
    dst = os.path.join(OUT, name)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(SRC, dst)
    tmp = tempfile.mkdtemp(prefix='towbeam_variant_')
    try:
        for lang in ('Rus', 'Eng'):
            dat = os.path.join(dst, 'CFG', lang, 'Lang.dat')
            js = os.path.join(tmp, lang + '.json')
            sr('dat', 'read', dat, '--json', '--out', js)
            doc = json.load(io.open(js, encoding='utf-8'))
            missing = set(changes) - apply(doc['entries'], changes)
            if missing:
                sys.exit('%s: нет TowBeam.Cfg.%s' % (dat, ', '.join(sorted(missing))))
            json.dump(doc, io.open(js, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=2)
            sr('dat', 'write', js, dat)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('готово:', dst, changes)


if __name__ == '__main__':
    main()
