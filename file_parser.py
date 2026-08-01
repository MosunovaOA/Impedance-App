import numpy as np

# ================= ФУНКЦИЯ ДЛЯ ПАРСИНГА ФАЙЛОВ =================
def parse_impedance_file(filepath):
    """
    Парсит файл с данными импеданса.
    Пропускает первые 4 строки (шапку).
    Затем читает данные: первый столбец пропускается,
    второй столбец - Zs' (ось X),
    третий столбец - Zs'' (ось Y).
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()

    data_lines = lines[4:]

    x_vals = []
    y_vals = []

    for line in data_lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        try:
            z_real = float(parts[1])
            z_imag = float(parts[2])
            x_vals.append(z_real)
            y_vals.append((-1) * (z_imag))  # Переворачиваем, чтобы Zs'' был положительным
        except ValueError:
            continue

    return np.array(x_vals), np.array(y_vals)