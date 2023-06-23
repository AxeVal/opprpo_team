import numpy as np
from numba import njit

from ..Properties import *

def IX(x: int, y: int, NN = N):
    return int(x + y * NN)

@njit
def set_bnd(b, x):
    """
    Устанавливает граничные условия для двумерного массива.

    Аргументы:
        b: Параметр граничного условия (не используется в функции).
        x: Двумерный массив, представляющий поле.

    Возвращает:
        x: Измененный двумерный массив с обновленными значениями на границе.

    Примечания:
        - Функция изменяет входной массив на месте.
        - Граничные значения устанавливаются как среднее значение соседних ячеек.
          Углы массива усредняются с двумя соседними ячейками.
    """
    x[0, 0]   = (x[1, 0]   + x[0, 1])   / 2
    x[0, -1]  = (x[1, -1]  + x[0, -2])  / 2
    x[-1, 0]  = (x[-2, 0]  + x[-1, 1])  / 2
    x[-1, -1] = (x[-2, -1] + x[-1, -2]) / 2
    return x

def advect(b, d, d0, Vx, Vy, dt, NN = N):
    """
    Производит перенос (адвекцию) значения плотности через векторное поле скорости.

    Аргументы:
        b: Параметр граничных условий (не используется в функции).
        d: Текущая плотность.
        d0: Исходная плотность.
        Vx: Компонента скорости по оси X.
        Vy: Компонента скорости по оси Y.
        dt: Шаг времени.
        NN: Размерность массива (по умолчанию равна N).

    Возвращает:
        d: Измененная плотность после адвекции.

    Примечания:
        - Функция осуществляет перенос плотности через векторное поле скорости.
        - Перенос происходит с использованием метода конечных разностей.
        - Граничные условия на массиве задаются с помощью функции set_bnd.
    """
    dtx = dt * (NN - 2)
    dty = dt * (NN - 2)

    tmp1 = dtx * Vx
    tmp2 = dty * Vy
    i = np.arange(0, NN)
    j = np.arange(0, NN)
    j, i = np.meshgrid(i, j)

    x = i - tmp1
    y = j - tmp2
    x[x < .5]     = 0.5
    x[x > N + .5] = NN + 0.5
    y[y < .5]     = 0.5
    y[y > N + .5] = NN + 0.5
    i0 = np.floor(x).astype(np.int32)
    i1 = i0 + 1
    j0 = np.floor(y).astype(np.int32)
    j1 = j0 + 1
    i0 = np.clip(i0, 0, NN - 1)
    i1 = np.clip(i1, 0, NN - 1)
    j0 = np.clip(j0, 0, NN - 1)
    j1 = np.clip(j1, 0, NN - 1)

    s1 = x - i0
    s0 = 1 - s1
    t1 = y - j0
    t0 = 1 - t1
    d = (s0 * (t0 * d0[i0, j0] +
               t1 * d0[i0, j1]) +
         s1 * (t0 * d0[i1, j0] +
               t1 * d0[i1, j1]))
    d = set_bnd(b, d)
    return d

@njit
def lin_solve(b, x, x0, a, c):
    """
    Решает линейную систему уравнений с помощью итерационного метода.

    Аргументы:
        b: Параметр граничных условий (не используется в функции).
        x: Текущее решение.
        x0: Исходное значение решения.
        a: Коэффициент перед суммой соседних значений.
        c: Коэффициент перед текущим значением.

    Возвращает:
        x: Решение линейной системы после заданного числа итераций.

    Примечания:
        - Функция решает линейную систему уравнений с помощью итерационного метода.
        - Решение получается путем суммирования соседних значений и деления на коэффициент c.
        - Граничные условия на массиве задаются с помощью функции set_bnd.
    """
    cRecip = 1.0 / c
    for k in range(iter):
        x[1:-1, 1:-1] = (x0[1:-1, 1:-1] + a * (x[:-2, 1:-1] +
                                               x[2:, 1:-1] +
                                               x[1:-1, :-2] +
                                               x[1:-1, 2:])) * cRecip
        x = set_bnd(b, x)
    return x

def diffuse(b, x, x0, diff, dt, NN = N):
    """
    Производит диффузию значения на двумерной сетке.

    Аргументы:
        b: Параметр граничных условий (не используется в функции).
        x: Текущее значение.
        x0: Исходное значение.
        diff: Коэффициент диффузии.
        dt: Шаг времени.

    Возвращает:
        x: Измененное значение после диффузии.

    Примечания:
        - Функция применяет диффузию к значению на двумерной сетке.
        - Диффузия выполняется путем решения линейной системы уравнений
          с использованием функции lin_solve.
        - Граничные условия на массиве задаются с помощью функции set_bnd.
    """
    a = dt * diff * (NN-2) * (NN-2)
    x = lin_solve(b, x, x0, a, 1+6*a)
    return x

@njit
def project(velocX, velocY, p, div, NN = N):
    """
    Выполняет проекцию поля скорости на двумерной сетке.

    Аргументы:
        velocX: Компонента скорости по оси X.
        velocY: Компонента скорости по оси Y.
        p: Давление.
        div: Дивергенция.
        NN: Размерность массива (по умолчанию равна N).

    Возвращает:
        velocX: Обновленная компонента скорости по оси X.
        velocY: Обновленная компонента скорости по оси Y.
        p: Обновленное давление.
        div: Обновленная дивергенция.

    Примечания:
        - Функция выполняет проекцию поля скорости на двумерной сетке.
        - Вычисляет дивергенцию и решает линейную систему уравнений для давления.
        - Обновляет компоненты скорости с учетом решенного давления.
        - Граничные условия на массивах задаются с помощью функции set_bnd.
    """
    for j in range(1, NN-1):
        for i in range(1, NN-1):
            div[i, j] = -0.5 * (velocX[i+1, j] -
                                    velocX[i-1, j] +
                                    velocY[i, j+1] -
                                    velocY[i, j-1]) / NN
            p[i, j] = 0
    div = set_bnd(0, div)
    p = set_bnd(0, p)
    p = lin_solve(0, p, div, 1, 6)

    for j in range(1, NN-1):
        for i in range(1, NN-1):
            velocX[i, j] -= 0.5 * (p[i+1, j] - p[i-1, j] +
                                   p[i, j+1] - p[i, j-1]) * NN
            velocY[i, j] -= 0.5 * (p[i+1, j] - p[i-1, j] +
                                   p[i, j+1] - p[i, j-1]) * NN
    velocX = set_bnd(1, velocX)
    velocY = set_bnd(2, velocY)
    return velocX, velocY, p, div