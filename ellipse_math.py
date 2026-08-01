import numpy as np

# ================= ФУНКЦИЯ ЭЛЛИПСА =================
def ellipse_center_on_x(x, x0, a, b):
    inside = 1 - ((x - x0) / a) ** 2
    inside = np.clip(inside, 0, 1)
    return b * np.sqrt(inside)