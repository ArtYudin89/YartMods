"""Проверка в окне игры: сейв загружается вариантом движка sr-lab `srlab` (`-srlab-load`) в окне
1280x720, затем по шагам — клавиши, щелчки, снимки; в конце окно закрывается.

Окно должно быть впереди (игра не замечает ввод в фоне), курсор переносится по-настоящему —
во время прогона компьютером не пользоваться. Звук выключен настройками sr-lab.
Сейв должен нести экран после загрузки (сейвы лаборатории sr-lab с экраном 0 игра закрывает
сразу после загрузки — `sr save playable`, память project_sr_lab).

Запуск из корня проекта:
    python tools/window_session.py <сейв> <профиль> <шаги.json> [папка мода]
Папка мода по умолчанию — build-debug/. Набор модов — переменная VS_MODS
(по умолчанию «Tweaks/UtilityFunctionsPack,Artem/TowBeam»). Снимки — в .window/shots/.

Шаги (координаты — в клиентской области окна):
    {"wait": с}  {"shot": "имя"}  {"key": "0"}  {"combo": ["SHIFT", "0"]}
    {"click": [x, y]}  {"rclick": [x, y]}  {"move": [x, y]}  {"log": N} — последние строки журнала игры
У любого шага — "pause": пауза после него (по умолчанию 0,6 с).
Shift в combo нажимается настоящим вводом: игра читает модификаторы через IsVirtualKeyDown.
"""

import ctypes
import io
import json
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(os.path.dirname(ROOT), 'sr-lab')
sys.path.insert(0, LAB)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

from srengine import runner  # noqa: E402
from srrun import input as gameinput, shot, window  # noqa: E402

SHOTS = os.path.join(ROOT, '.window', 'shots')
DEFAULT_MODS = 'Tweaks/UtilityFunctionsPack,Artem/TowBeam'


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    save, profile, steps_path = sys.argv[1], sys.argv[2], sys.argv[3]
    tow = sys.argv[4] if len(sys.argv) > 4 else os.path.join(ROOT, 'build-debug')
    steps = json.load(io.open(steps_path, encoding='utf-8'))
    mods = os.environ.get('VS_MODS', DEFAULT_MODS).split(',')
    log_path = os.path.join(LAB, '.local', 'profiles', profile, 'Documents', 'SpaceRangersHD', '########.log')
    os.makedirs(SHOTS, exist_ok=True)
    outcome = {}

    def run():
        started = time.time()
        try:
            result = runner.run(save, lambda s, box: ['-srlab-load', s], variant='srlab', profile=profile,
                                timeout=900, monitor=0, mod_ids=mods, overrides={'Artem\\TowBeam': tow},
                                log=lambda *a: None)
            outcome['text'] = 'игра вышла с кодом %s через %.1f с' % (result.get('exit_code'), time.time() - started)
        except runner.RunnerError as error:
            outcome['text'] = 'ошибка запуска: ' + str(error)[:300]

    thread = threading.Thread(target=run)
    thread.start()
    window.dpi_aware()
    start = time.time()
    hwnd = None
    while thread.is_alive() and time.time() - start < 60:
        hwnd = window.game_window()
        if hwnd and window.state(hwnd)['visible']:
            rect = window.client_rect(hwnd)
            if rect[2] - rect[0] == 1280:
                break
        time.sleep(0.5)
    print('%5.1f с окно %s' % (time.time() - start, hwnd))
    for step in steps:
        if not thread.is_alive():
            print('игры уже нет')
            break
        hwnd = window.game_window() or hwnd
        stamp = '%5.1f с' % (time.time() - start)
        if 'wait' in step:
            time.sleep(step['wait'])
            continue
        gameinput.activate(hwnd)
        if 'shot' in step:
            path = os.path.join(SHOTS, '%s.png' % step['shot'])
            shot.capture_window(hwnd, path)
            print(stamp, 'снимок', path)
        elif 'key' in step:
            gameinput.key(hwnd, step['key'])
            print(stamp, 'клавиша', step['key'])
        elif 'combo' in step:
            modifier = gameinput.key_code(step['combo'][0])
            ctypes.windll.user32.keybd_event(modifier, 0, 0, 0)
            time.sleep(0.15)
            try:
                gameinput.key(hwnd, step['combo'][1])
                time.sleep(0.15)
            finally:
                ctypes.windll.user32.keybd_event(modifier, 0, 2, 0)  # KEYEVENTF_KEYUP
            print(stamp, 'клавиши', '+'.join(step['combo']))
        elif 'click' in step:
            gameinput.click(hwnd, *step['click'])
            print(stamp, 'щелчок', step['click'])
        elif 'rclick' in step:
            gameinput.click(hwnd, *step['rclick'], button='right')
            print(stamp, 'правый щелчок', step['rclick'])
        elif 'move' in step:
            gameinput.move(hwnd, *step['move'])
            print(stamp, 'курсор', step['move'])
        elif 'log' in step:
            try:
                lines = io.open(log_path, encoding='cp1251', errors='replace').read().splitlines()
            except OSError:
                lines = ['(журнала нет)']
            for line in lines[-step['log']:]:
                print(stamp, 'журнал |', line)
        time.sleep(step.get('pause', 0.6))
    if thread.is_alive():
        window.ask_close(window.game_window() or hwnd)
        thread.join(30)
    print(outcome.get('text', 'игра не закрылась по просьбе'))


if __name__ == '__main__':
    main()
