# Funciones para construir horarios y verificar compatibilidad entre cursos.

import re
import pandas as pd


def build_schedule(course_row, schedule_columns, start_module, end_module):
    """
    Construye el horario de un curso expresado en módulos.

    El resultado es un diccionario por día:
        L, M, W, J, V, S

    donde cada día contiene los módulos ocupados por el curso.

    También devuelve el campus del curso.
    """
    schedule = {day: [] for day in "LMWJVS"}

    # Ejemplo esperado:
    # L:0820 a 0930
    pattern = re.compile(r"([LMWJVS]):(\d{4})\s*a\s*(\d{4})")

    for column in schedule_columns:
        if pd.isna(course_row[column]):
            continue

        text = str(course_row[column])

        # Una misma celda puede contener varios bloques separados por ";"
        for part in text.split(";"):
            part = part.strip()

            if not part:
                continue

            match = pattern.search(part)

            if not match:
                continue

            day, start_time, end_time = match.groups()

            # Si el horario no corresponde a módulos conocidos, se ignora.
            if start_time not in start_module or end_time not in end_module:
                continue

            start = start_module[start_time]
            end = end_module[end_time]

            schedule[day].extend(range(start, end + 1))

    campus = str(course_row["campus"]).strip()

    return schedule, campus


def are_compatible_all(
    course_rows,
    schedule_columns,
    start_module,
    end_module,
):
    """
    Verifica que todos los cursos sean compatibles entre sí.

    Una combinación se considera incompatible si:

    1. Dos cursos ocupan el mismo módulo el mismo día.
    2. Dos cursos están en campus distintos y tienen módulos contiguos,
       porque no existiría tiempo suficiente para realizar el traslado.
    """
    schedules = []
    campuses = []

    # Construir horario y campus de cada curso.
    for _, row in course_rows.iterrows():
        schedule, campus = build_schedule(
            row,
            schedule_columns,
            start_module,
            end_module,
        )

        schedules.append(schedule)
        campuses.append(campus)

    # Comparar todos los pares de cursos.
    for i in range(len(schedules)):
        for j in range(i + 1, len(schedules)):
            campus_i = campuses[i]
            campus_j = campuses[j]

            for day in "LMWJVS":
                modules_i = set(schedules[i][day])
                modules_j = set(schedules[j][day])

                # Conflicto directo de horario.
                if modules_i & modules_j:
                    return False

                # Si los campus son distintos, tampoco se permiten
                # módulos inmediatamente consecutivos.
                if campus_i != campus_j:
                    for module in modules_i:
                        if (
                            module + 1 in modules_j
                            or module - 1 in modules_j
                        ):
                            return False

    return True