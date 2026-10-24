"""Пакет для тестера: dist/TowBeam_test.zip (тестовая сборка в Mods/Artem/TowBeam + инструкция).

Берёт build-debug/ (сначала python -m srmod build и python tools/make_debug.py) и инструкцию
dist/«TowBeam — инструкция для тестера.txt» (пишется в UTF-8 с BOM и переводами строк Windows,
чтобы открывалась Блокнотом). Сейв dist/TowBeam_test.sav делает тест лаборатории tests/make-save.json.
"""

import io
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build-debug")
DIST = os.path.join(ROOT, "dist")
GUIDE = "TowBeam — инструкция для тестера.txt"
ZIP = "TowBeam_test.zip"


def normalize_guide(path):
    with io.open(path, encoding="utf-8-sig") as handle:
        text = handle.read()
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(path, "wb") as handle:
        handle.write(b"\xef\xbb\xbf" + text.encode("utf-8"))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if not os.path.isdir(BUILD):
        sys.exit("нет build-debug/ — сначала python tools/make_debug.py")
    guide = os.path.join(DIST, GUIDE)
    if not os.path.isfile(guide):
        sys.exit("нет инструкции: %s" % guide)
    normalize_guide(guide)
    target = os.path.join(DIST, ZIP)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder, _dirs, files in os.walk(BUILD):
            for name in sorted(files):
                full = os.path.join(folder, name)
                rel = os.path.relpath(full, BUILD).replace(os.sep, "/")
                archive.write(full, "Mods/Artem/TowBeam/" + rel)
        archive.write(guide, GUIDE)
    with zipfile.ZipFile(target) as archive:
        for info in archive.infolist():
            print("%9d  %s" % (info.file_size, info.filename))
    print()
    for name in sorted(os.listdir(DIST)):
        print("%9d  %s" % (os.path.getsize(os.path.join(DIST, name)), name))


if __name__ == "__main__":
    main()
