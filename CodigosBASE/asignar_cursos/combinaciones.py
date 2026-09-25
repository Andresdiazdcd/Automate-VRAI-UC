# Generación y evaluación de combinaciones de cursos por estudiante.

from itertools import combinations

import pandas as pd

from horarios import are_compatible_all


def score_combo(student_rows, idxs, priority_values):
    """
    Calcula el puntaje total de una combinación de cursos.

    El puntaje se obtiene sumando el valor asociado a la prioridad
    de cada curso seleccionado.
    """
    total = 0

    for i in idxs:
        priority = pd.to_numeric(
            student_rows.iloc[i]["prioridad"],
            errors="coerce",
        )

        if pd.isna(priority):
            return None

        total += priority_values.get(int(priority), 0)

    return total


def generate_best_combos_per_student(
    df_students,
    df_courses,
    k,
    schedule_columns,
    start_module,
    end_module,
    priority_values,
):
    """
    Genera las combinaciones compatibles de K cursos para cada estudiante.

    Devuelve
    --------
    df_combinations:
        Todas las combinaciones compatibles encontradas.

    df_best:
        La mejor combinación de cada estudiante, definida como aquella
        con mayor puntaje total de prioridad.
    """
    all_rows = []
    best_rows = []

    # Solo considerar solicitudes de cursos pertenecientes al catálogo.
    df_students = df_students[
        df_students["curso_dentro_del_catalogo"] == "Sí"
    ].copy()

    for rut, student_rows in df_students.groupby("rut_uc"):
        student_rows = student_rows.reset_index(drop=True)

        # No es posible formar una combinación de K cursos.
        if len(student_rows) < k:
            continue

        best_score = None
        best_combo = None

        # Generar todas las combinaciones posibles de tamaño K.
        for idxs in combinations(range(len(student_rows)), k):

            # No se permite repetir una misma sigla dentro de la combinación.
            siglas = list(
                student_rows.loc[list(idxs), "sigla"].astype(str)
            )

            if len(set(siglas)) != k:
                continue

            nrcs = list(
                student_rows.loc[list(idxs), "nrc"].astype(str)
            )

            # Recuperar los cursos correspondientes desde el catálogo.
            course_rows = df_courses[
                df_courses["nrc"].astype(str).isin(nrcs)
            ]

            # Todos los cursos de la combinación deben existir en el catálogo.
            if len(course_rows) != k:
                continue

            # Verificar compatibilidad de horarios y campus.
            if not are_compatible_all(
                course_rows,
                schedule_columns,
                start_module,
                end_module,
            ):
                continue

            # Calcular puntaje de la combinación.
            score = score_combo(
                student_rows,
                idxs,
                priority_values,
            )

            if score is None:
                continue

            row = {
                "RUT UC": rut,
                "Nombre": student_rows.loc[0, "nombre_completo"],
                "Score_total": score,
            }

            # Guardar el detalle de cada curso de la combinación.
            for j, i in enumerate(idxs, start=1):
                row[f"Curso {j} - NRC"] = str(
                    student_rows.loc[i, "nrc"]
                )

                row[f"Curso {j} - Sigla"] = str(
                    student_rows.loc[i, "sigla"]
                )

                row[f"Curso {j} - Unidad Académica"] = str(
                    student_rows.loc[i, "unidad_academica"]
                )

                row[f"Curso {j} - Prioridad"] = str(
                    student_rows.loc[i, "prioridad"]
                )

                row[f"Curso {j} - Convenio"] = bool(
                    student_rows.loc[i, "convenio_activo"]
                )

                row[f"Curso {j} - ReqGrad"] = str(
                    student_rows.loc[
                        i,
                        "necesitas_este_curso_para_la_obtencion_del_grado_en_tu_universidad_de_origen",
                    ]
                )

            all_rows.append(row)

            # Conservar la combinación de mayor puntaje.
            if best_score is None or score > best_score:
                best_score = score
                best_combo = row

        if best_combo is not None:
            best_rows.append(best_combo)

    df_combinations = pd.DataFrame(all_rows)
    df_best = pd.DataFrame(best_rows)

    return df_combinations, df_best