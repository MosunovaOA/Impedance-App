import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.optimize import minimize

from file_parser import parse_impedance_file
from ellipse_math import ellipse_center_on_x

# ================= ОСНОВНОЕ ПРИЛОЖЕНИЕ =================
class ImpedanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Аппроксимация годографа эллипсом | Автор: Мосунова О.А.")

        # Устанавливаем размер окна 1680x1050 в левом верхнем углу
        self.root.geometry("1680x1010+-8+0")

        # Данные
        self.x_vals = None
        self.y_vals = None
        self.current_file = None

        # Параметры
        self.skip_first_n = tk.IntVar(value=0)
        self.num_increasing = tk.IntVar(value=0)
        self.num_decreasing = tk.IntVar(value=3)
        self.decreasing_weight = tk.DoubleVar(value=5.0)
        self.skip_last_n = tk.IntVar(value=0)

        # Привязываем обновление к изменению переменных
        self.skip_first_n.trace_add('write', lambda *args: self.update_plot())
        self.num_increasing.trace_add('write', lambda *args: self.update_plot())
        self.num_decreasing.trace_add('write', lambda *args: self.update_plot())
        self.decreasing_weight.trace_add('write', lambda *args: self.update_plot())
        self.skip_last_n.trace_add('write', lambda *args: self.update_plot())

        # Результаты аппроксимации
        self.x0_fit = None
        self.a_fit = None
        self.b_fit = None
        self.x_right = None
        self.x_left_fit = None
        self.x_inc = None
        self.y_inc = None
        self.x_dec = None
        self.y_dec = None
        self.x_vals_trimmed = None
        self.y_vals_trimmed = None
        self.max_x_trimmed = None
        self.max_y_trimmed = None
        self.x_left = None

        self.create_widgets()

    def create_widgets(self):
        # Левая панель с настройками
        left_frame = tk.Frame(self.root, width=250, bg='lightgray', relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_frame.pack_propagate(False)  # Запрещаем сжатие

        # Правая панель с графиком
        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        info_text = tk.Label(left_frame, text="📄 Информация о формате файла",
                             bg='lightgray', fg='darkblue', font=('Arial', 8, 'bold'))
        info_text.pack(fill=tk.X, padx=10, pady=5)

        # Добавляем всплывающую подсказку
        def show_info(event):
            messagebox.showinfo("Формат файла",
                                "Файл должен быть в формате .dat или .txt.\n"
                                "Обязательна шапка в четыре строки, после которой\n"
                                "идут данные в виде столбцов, разделенных пробелами.\n"
                                "Первый столбец - Freq.[Hz], второй - Zs'[Ohms],\n"
                                "третий - Zs\"[Ohms], последующие столбцы -\n"
                                "опциональны и в рассчетах не участвуют.")

        info_text.bind("<Button-1>", show_info)  # Клик мышью для показа

        # Кнопка выбора файла
        tk.Button(left_frame, text="Выбрать файл с данными", command=self.load_file,
                  bg='lightblue', font=('Arial', 10), height=2).pack(fill=tk.X, padx=10, pady=10)

        # Метка с именем файла
        self.file_label = tk.Label(left_frame, text="Файл не выбран", bg='lightgray', font=('Arial', 10))
        self.file_label.pack(fill=tk.X, padx=10, pady=5)

        # Разделитель
        tk.Frame(left_frame, height=2, bg='gray').pack(fill=tk.X, padx=10, pady=10)

        # Настройки
        tk.Label(left_frame, text="НАСТРОЙКИ", bg='lightgray', font=('Arial', 12, 'bold')).pack(pady=10)

        # Пропустить первых N точек
        frame1 = tk.Frame(left_frame, bg='lightgray')
        frame1.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(frame1, text="Пропустить первых \nточек:", bg='lightgray', width=18, anchor='w', justify=tk.LEFT).pack(side=tk.LEFT)
        tk.Spinbox(frame1, from_=0, to=100, textvariable=self.skip_first_n, width=8).pack(side=tk.RIGHT)

        # Возрастающих точек (0 = все)
        frame2 = tk.Frame(left_frame, bg='lightgray')
        frame2.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(frame2, text="Использовать\nточек\nвозрастающей\n(0=исп. все):", bg='lightgray', width=18, anchor='w', justify=tk.LEFT).pack(
            side=tk.LEFT)
        tk.Spinbox(frame2, from_=0, to=100, textvariable=self.num_increasing, width=8).pack(side=tk.RIGHT)

        # Убывающих точек
        frame3 = tk.Frame(left_frame, bg='lightgray')
        frame3.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(frame3, text="Использовать \nточек убывающей:", bg='lightgray', width=18, anchor='w', justify=tk.LEFT).pack(side=tk.LEFT)
        tk.Spinbox(frame3, from_=0, to=100, textvariable=self.num_decreasing, width=8).pack(side=tk.RIGHT)

        # Вес для убывающих точек
        frame4 = tk.Frame(left_frame, bg='lightgray')
        frame4.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(frame4, text="Вес точек \nубывающей:", bg='lightgray', width=18, anchor='w', justify=tk.LEFT).pack(side=tk.LEFT)
        tk.Scale(frame4, from_=1, to=100, resolution=0.5, orient=tk.HORIZONTAL,
                 variable=self.decreasing_weight).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        frame5 = tk.Frame(left_frame, bg='lightgray')
        frame5.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(frame5, text="Исключить \nпоследних точек:", bg='lightgray', width=18, anchor='w',
                 justify=tk.LEFT).pack(side=tk.LEFT)
        tk.Spinbox(frame5, from_=0, to=100, textvariable=self.skip_last_n, width=8).pack(side=tk.RIGHT)

        # ===== КНОПКА С ИНФОРМАЦИЕЙ О РЕШАТЕЛЕ =====
        solver_info = tk.Label(left_frame, text="📄 Информация о решателе",
                               bg='lightgray', fg='darkred', font=('Arial', 8, 'bold'))
        solver_info.pack(fill=tk.X, padx=10, pady=5)

        def show_solver_info(event):
            messagebox.showinfo("О решателе",
                                "Решатель не всегда способен построить эллипс.\n"
                                "Пробуйте разные настройки.\n\n"
                                "Часто бывает полезно изменить вес точек убывающей.\n"
                                "Вес точек убывающей отвечает за величину штрафа,\n"
                                "которая определяет, насколько эллипс будет \"стараться\"\n"
                                "проходить ниже точек убывающей ветви годографа.\n\n"
                                "Настройка \"пропустить первых точек\" позволяет\n"
                                "исключить из рассчетов эллипса указанное количество\n"
                                "точек с начала файла. Бывает полезна, если в начале \n"
                                "измерений присутствуют шум или выбросы, которые \n"
                                "мешают корректной аппроксимации.\n\n"
                                "Настройка \"использовать точек возрастающей\"\n"
                                "ограничивает количество точек на возрастающей ветви\n"
                                "годографа. Значение 0 означает, что используются\n"
                                "все точки, от начала до точки максимума включительно.\n"
                                "Числа, бóльшие 0, могут помочь, если некоторые \n"
                                "точки, идущие подряд, сильно отклоняются от формы эллипса.\n\n"
                                "Настройка \"использовать точек убывающей\" определяет,\n"
                                "сколько точек на убывающей ветви годографа (включая\n"
                                "максимум) будет использовано для аппроксимации.\n\n"
                                "Программа ориентируется на точку с самой большой\n"
                                "координатой по оси 0y для выбора точки вершины\n"
                                "эллипса, поэтому при необходимости следует\n"
                                "ограничить число точек, использующихся для\n"
                                "вычислений. Для этого пользуйтесь настройкой\n"
                                "\"исключить последних точек\".\n\n"
                                )

        solver_info.bind("<Button-1>", show_solver_info)

        # Разделитель
        tk.Frame(left_frame, height=2, bg='gray').pack(fill=tk.X, padx=10, pady=10)

        # Результаты аппроксимации - заголовок по центру
        tk.Label(left_frame, text="РЕЗУЛЬТАТЫ", bg='lightgray', font=('Arial', 12, 'bold')).pack(pady=(10, 5))

        self.result_text = tk.Text(left_frame, height=13, width=40, font=('Courier', 9))
        self.result_text.pack(fill=tk.X, padx=10, pady=5)

        # Кнопка копирования только Rbulk
        tk.Button(left_frame, text="📋 Копировать Rbulk", command=self.copy_rbulk,
                  bg='lightgreen', font=('Arial', 9)).pack(fill=tk.X, padx=10, pady=(0, 5))

        # Создаём фигуру для графика
        self.fig = Figure(figsize=(10, 8), dpi=130)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def copy_rbulk(self):
        """Копирует только значение Rbulk в буфер обмена"""
        if self.a_fit is not None:
            rbulk_value = self.a_fit * 2
            text = f"{rbulk_value:.3e}"
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.show_temp_message(f"✅ Rbulk = {text} Ом скопирован!")
        else:
            self.show_temp_message("⚠️ Нет данных Rbulk для копирования")
    def show_temp_message(self, message):
        """Показывает временное сообщение в строке состояния"""
        temp_label = tk.Label(self.root, text=message, bg='lightgreen', font=('Arial', 10))
        temp_label.place(relx=0.5, rely=0.98, anchor='center')
        self.root.after(2000, temp_label.destroy)

    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите файл с данными",
            filetypes=[("Data files", "*.dat"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            self.file_label.config(text=f"Файл: {os.path.basename(file_path)}")
            self.update_plot()

    def fit_ellipse(self):
        """Аппроксимация эллипса с сохранением пропорций"""
        if self.x_vals is None or len(self.x_vals) == 0:
            return False

        skip_n = self.skip_first_n.get()
        skip_last_n = self.skip_last_n.get()

        # Обрезаем сначала первые, потом последние точки
        x_temp = self.x_vals[skip_n:]
        y_temp = self.y_vals[skip_n:]

        if skip_last_n > 0:
            x_trimmed = x_temp[:-skip_last_n]
            y_trimmed = y_temp[:-skip_last_n]
        else:
            x_trimmed = x_temp
            y_trimmed = y_temp

        if len(x_trimmed) == 0:
            return False

        # Находим максимум для определения возрастающей/убывающей ветви
        max_idx = np.argmax(y_trimmed)
        max_y = y_trimmed[max_idx]
        max_x = x_trimmed[max_idx]

        # Возрастающая ветвь
        num_inc = self.num_increasing.get()
        if num_inc == 0:
            x_inc = x_trimmed[:max_idx + 1]
            y_inc = y_trimmed[:max_idx + 1]
        else:
            x_inc = x_trimmed[:num_inc]
            y_inc = y_trimmed[:num_inc]

        # Убывающая ветвь
        num_dec = self.num_decreasing.get()
        if num_dec > 0:
            x_dec = x_trimmed[max_idx:max_idx + num_dec]
            y_dec = y_trimmed[max_idx:max_idx + num_dec]
        else:
            x_dec = np.array([])
            y_dec = np.array([])

        if len(x_inc) == 0:
            return False

        x_left = x_inc[0]
        weight = self.decreasing_weight.get()

        # ===== НОРМАЛИЗАЦИЯ С СОХРАНЕНИЕМ ПРОПОРЦИЙ =====
        # Масштабируем X и Y так, чтобы максимальные значения стали равны 1
        x_max_data = np.max(x_trimmed)
        y_max_data = np.max(y_trimmed)

        x_scale = x_max_data
        y_scale = y_max_data

        x_norm = x_trimmed / x_scale
        y_norm = y_trimmed / y_scale

        x_inc_norm = x_inc / x_scale
        y_inc_norm = y_inc / y_scale

        if len(x_dec) > 0:
            x_dec_norm = x_dec / x_scale
            y_dec_norm = y_dec / y_scale
        else:
            x_dec_norm = np.array([])
            y_dec_norm = np.array([])

        x_left_norm = x_left / x_scale
        max_y_norm = max_y / y_scale

        # Целевая функция
        def objective(params):
            x0, a, b = params
            if a <= 0 or b <= 0:
                return 1e10

            y_inc_pred = ellipse_center_on_x(x_inc_norm, x0, a, b)
            error_inc = np.sum((y_inc_norm - y_inc_pred) ** 2)

            error_dec = 0
            if len(x_dec_norm) > 0:
                y_dec_pred = ellipse_center_on_x(x_dec_norm, x0, a, b)
                for i in range(len(x_dec_norm)):
                    diff = y_dec_norm[i] - y_dec_pred[i]
                    if diff < 0:
                        error_dec += weight * (diff ** 2) * 10
                    else:
                        error_dec += (diff ** 2)


            return error_inc + error_dec

        # Начальные приближения
        x_right_guess_norm = min(x_norm[-1] * 1.2, 1.5)
        x0_guess = (x_left_norm + x_right_guess_norm) / 2
        a_guess = (x_right_guess_norm - x_left_norm) / 2
        b_guess = max_y_norm

        result = minimize(objective, [x0_guess, a_guess, b_guess],
                          method='L-BFGS-B',
                          bounds=[(x_left_norm, 1.5),
                                  (0.01, 2.0),
                                  (0.01, 2.0)])

        if result.success:
            x0_norm, a_norm, b_norm = result.x

            # ОБРАТНОЕ ПРЕОБРАЗОВАНИЕ
            self.x0_fit = x0_norm * x_scale
            self.a_fit = a_norm * x_scale
            self.b_fit = b_norm * y_scale

            self.x_right = self.x0_fit + self.a_fit
            self.x_left_fit = self.x0_fit - self.a_fit

            # Сохраняем данные для отрисовки
            self.x_inc = x_inc
            self.y_inc = y_inc
            self.x_dec = x_dec
            self.y_dec = y_dec
            self.max_x_trimmed = max_x
            self.max_y_trimmed = max_y
            self.x_left = x_left

            print(f"\n=== ДИАГНОСТИКА ===")
            print(f"Масштабы: x_scale={x_scale:.2e}, y_scale={y_scale:.2e}")
            print(f"Норм.: x0={x0_norm:.3f}, a={a_norm:.3f}, b={b_norm:.3f}")
            print(f"Исх.: x0={self.x0_fit:.2e}, a={self.a_fit:.2e}, b={self.b_fit:.2e}")
            print(f"Rs={self.x_right:.2e}")

            return True
        return False

    def update_plot(self):
        if self.current_file is None:
            return

        # Загружаем данные
        self.x_vals, self.y_vals = parse_impedance_file(self.current_file)

        if len(self.x_vals) == 0:
            return

        # Аппроксимируем
        success = self.fit_ellipse()

        # Очищаем график
        self.ax.clear()

        # Рисуем данные
        skip_n = self.skip_first_n.get()
        skip_last_n = self.skip_last_n.get()

        # Отображаем пропущенные первые точки (если есть)
        if skip_n > 0:
            self.ax.plot(self.x_vals[:skip_n], self.y_vals[:skip_n], 'c-o',
                         linewidth=1, markersize=3, alpha=0.5, label=f'Пропущенные ({skip_n})')

        # Определяем диапазон для остальных данных (исключаем последние N точек)
        start_idx = skip_n
        end_idx = len(self.x_vals) - skip_last_n if skip_last_n > 0 else len(self.x_vals)

        # Отображаем остальные точки (участвуют в расчётах)
        if start_idx < end_idx:
            self.ax.plot(self.x_vals[start_idx:end_idx], self.y_vals[start_idx:end_idx], 'b-o',
                         linewidth=1, markersize=3, alpha=0.3, label='Остальные данные')

        if success:
            # Возрастающая ветвь
            self.ax.plot(self.x_inc, self.y_inc, 'ro-', linewidth=2, markersize=6,
                         label=f'Возрастающая ({len(self.x_inc)})')

            # Убывающая ветвь
            if len(self.x_dec) > 0:
                self.ax.plot(self.x_dec, self.y_dec, 'yo-', linewidth=2, markersize=6,
                             label=f'Убывающая ({len(self.x_dec)})')

            # Эллипс (рисуем в ИСХОДНЫХ координатах)
            x_fit = np.linspace(self.x_left_fit, self.x_right, 500)
            y_fit = ellipse_center_on_x(x_fit, self.x0_fit, self.a_fit, self.b_fit)
            self.ax.plot(x_fit, y_fit, 'k', linewidth=2.5, label='Аппроксимация\nэллипсом')

            # Центр
            self.ax.plot(self.x0_fit, 0, 'r+', markersize=12, linewidth=5,
                         label=f'Центр (x₀):\n{self.x0_fit:.3e})')
            self.ax.axvline(x=self.x0_fit, color='red', linestyle=':', alpha=0.5)

            # Rs
            self.ax.plot(self.x_right, 0, 'm*', markersize=20, label=f'Rs:\n{self.x_right:.3e} Ом')
            self.ax.axvline(x=self.x_right, color='magenta', linestyle='--', alpha=0.7)

            # Левое пересечение
            self.ax.plot(self.x_left_fit, 0, 'mP', markersize=18, label=f'Левое пересеч.:\n{self.x_left_fit:.3e}')

            # Начальная точка
            self.ax.plot(self.x_left, 0, 'kX', markersize=12, label=f'Начальная точка\nв проекции\nна ось x:\n{self.x_left:.3e}')

            # Максимум
            self.ax.plot(self.max_x_trimmed, self.max_y_trimmed, 'k*', markersize=10,
                         label=f'Максимум:\n{self.max_y_trimmed:.3e}')

            # Стрелки для полуосей
            y_max_arrows = max(self.max_y_trimmed, self.b_fit)
            self.ax.annotate('', xy=(self.x0_fit + self.a_fit, 0), xytext=(self.x0_fit, 0),
                             arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
            self.ax.text(self.x0_fit + self.a_fit / 2, -y_max_arrows * 0.025, f'a={self.a_fit:.3e}',
                         ha='center', fontsize=9, color='black')

            self.ax.annotate('', xy=(self.x0_fit, self.b_fit), xytext=(self.x0_fit, 0),
                             arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
            self.ax.text(self.x0_fit + self.max_x_trimmed * 0.02, self.b_fit / 2, f'b={self.b_fit:.3e}',
                         va='center', fontsize=9, color='black')

            # Обновляем текстовые результаты
            result_str = f"ПАРАМЕТРЫ ЭЛЛИПСА:\n"
            result_str += f" Центр x₀: {self.x0_fit:.3e} Ом\n"
            result_str += f" Полуось a: {self.a_fit:.3e} Ом\n"
            result_str += f" Полуось b: {self.b_fit:.3e} Ом\n"
            result_str += f" Rs: {self.x_right:.3e} Ом\n"
            result_str += f" Rbulk = 2*a:\n  {(self.a_fit)*2:.3e} Ом\n"
            result_str += f" Левое пересеч.:\n  {self.x_left_fit:.3e} Ом\n\n"
            result_str += f"ТОЧКИ:\n"
            result_str += f" Возрастающей: {len(self.x_inc)}\n"
            result_str += f" Убывающей: {len(self.x_dec)}\n"
            result_str += f" Пропущено: {skip_n}\n\n"
            result_str += f"МАКСИМУМ:\n"
            result_str += f" x: {self.max_x_trimmed:.3e}\n"
            result_str += f" y: {self.max_y_trimmed:.3e}"

            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, result_str)

        # Проверка условия и визуализация (исключая точку максимума)
        condition_ok = True
        if success and len(self.x_dec) > 0:
            y_dec_pred = ellipse_center_on_x(self.x_dec, self.x0_fit, self.a_fit, self.b_fit)
            problem_x = []
            problem_y = []
            for i in range(len(self.x_dec)):
                # Проверяем, что это НЕ точка максимума
                # (можно сравнить с max_x_trimmed и max_y_trimmed с небольшой погрешностью)
                is_max_point = (abs(self.x_dec[i] - self.max_x_trimmed) < 1e-6 and
                                abs(self.y_dec[i] - self.max_y_trimmed) < 1e-6)

                if not is_max_point and self.y_dec[i] < y_dec_pred[i]:
                    problem_x.append(self.x_dec[i])
                    problem_y.append(self.y_dec[i])
                    condition_ok = False

            if not condition_ok:
                self.ax.scatter(problem_x, problem_y, color='red', s=150,
                                marker='X', linewidths=2, zorder=10,
                                label=f'Точки убывающей\nниже эллипса!')

        self.ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        self.ax.set_xlabel("Zs' [Ohms]", fontsize=12)
        self.ax.set_ylabel("-Zs'' [Ohms]", fontsize=12)
        self.ax.set_title(f"Аппроксимация годографа эллипсом\n{os.path.basename(self.current_file)}", fontsize=12)
        self.ax.grid(True, linestyle='--', alpha=0.5)

        # Легенда справа от графика
        self.ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=6, labelspacing=1.5, markerscale=0.6)
        # Добавляем отступ справа, чтобы легенда не обрезалась
        self.fig.subplots_adjust(right=0.82)

        self.canvas.draw()