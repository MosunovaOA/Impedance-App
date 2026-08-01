import matplotlib
matplotlib._check_versions = lambda: None

import tkinter as tk
from impedance_app import ImpedanceApp
import sys

# 1. Полностью блокируем kiwisolver на уровне builtins
_original_import = __builtins__.__import__


def _import_hook(name, *args, **kwargs):
    if name == 'kiwisolver' or name.startswith('kiwisolver.'):
        # Создаём фейковый модуль
        class _FakeModule:
            __version__ = '1.4.5'

            def __getattr__(self, _):
                return self

            def __call__(self, *args, **kwargs):
                return self

        fake = _FakeModule()
        sys.modules[name] = fake
        return fake
    return _original_import(name, *args, **kwargs)


__builtins__.__import__ = _import_hook

# 2. Подменяем в sys.modules на всякий случай
sys.modules['kiwisolver'] = _import_hook('kiwisolver')
sys.modules['kiwisolver._cext'] = _import_hook('kiwisolver._cext')


# ================= ЗАПУСК =================
if __name__ == "__main__":
    root = tk.Tk()
    app = ImpedanceApp(root)
    root.mainloop()