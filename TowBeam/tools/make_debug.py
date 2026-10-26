"""Отладочный вариант сборки: build/ -> build-debug/ с TowBeam.Cfg.Debug=1 в обоих Lang.dat.

В отладочном варианте клавиша 9 на карте системы кладёт рядом ящик минералов (150),
берёт его на буксир и даёт кораблю приказ лететь вперёд — удобно смотреть луч и груз глазами.
Датники правятся машинным видом sr-lab (`sr dat read --json` / `sr dat write`), без потерь.

Запуск из корня проекта после `python -m srmod build`:
    python tools/make_debug.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "sr-lab", "sr.py")  # next to the YartMods clone
SRC = os.path.join(ROOT, "build")
DST = os.path.join(ROOT, "build-debug")


def sr(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run([sys.executable, SR] + list(args), check=True, env=env,
                   stdout=subprocess.DEVNULL)


def set_debug(entries, path=()):
    """Найти параметр TowBeam/Cfg/Debug в машинном виде дерева и поставить 1; вернуть, нашли ли."""
    found = False
    for entry in entries:
        if entry.get("kind") == "block":
            found = set_debug(entry.get("entries", []), path + (entry.get("name"),)) or found
        elif entry.get("kind") == "param" and entry.get("name") == "Debug" and path == ("TowBeam", "Cfg"):
            entry["value"] = "1"
            found = True
    return found


def main():
    if not os.path.isdir(SRC):
        sys.exit("нет build/ — сначала python -m srmod build")
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    tmp = tempfile.mkdtemp(prefix="towbeam_debug_")
    try:
        for lang in ("Rus", "Eng"):
            dat = os.path.join(DST, "CFG", lang, "Lang.dat")
            js = os.path.join(tmp, lang + ".json")
            sr("dat", "read", dat, "--json", "--out", js)
            with open(js, encoding="utf-8") as handle:
                doc = json.load(handle)
            if not set_debug(doc["entries"]):
                sys.exit("%s: не нашёл TowBeam.Cfg.Debug" % dat)
            with open(js, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(doc, handle, ensure_ascii=False, indent=2)
            sr("dat", "write", js, dat)
            print("Debug=1:", dat)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("готово:", DST)


if __name__ == "__main__":
    main()
