# Flujo principal del algoritmo de asignación.
#
# Contiene:
# 1. Fase principal: asignación iterativa de K cursos.
# 2. Fase SINGLE: uso de vacantes restantes para asignar 1 curso adicional.

import os

import numpy as np
import pandas as pd

from datos_io import (
    load_data,
    save_output,
    save_next_formulario,
    find_last_file,
)

from horarios import are_compatible_all

from combinaciones import generate_best_combos_per_student

from asignacion import (
    add_convenio_activo,
    build_course_demand,
    sort_course_demand_like_original,
    assign_by_vacancies,
    split_success_fail,
)


def run_iterations_real(config, start_file, k_courses):
    """
    Ejecuta la fase principal de asignación.

    En cada iteración:
    - busca la mejor combinación de K cursos por estudiante;
    - reparte las vacantes;
    - considera exitosos a quienes obtienen los K cursos;
    - mantiene al resto para la siguiente iteración;
    - actualiza las vacantes disponibles.

    El proceso termina cuando ya no existen combinaciones viables
    o no se producen nuevas asignaciones exitosas.
    """
    iteration = 1
    current_file = start_file
    k = k_courses

    while os.path.exists(current_file):

        print(
            f"\n[REAL] Ejecutando iteración {iteration} "
            f"| Archivo: {current_file}"
        )

        # ---------------------------------------------------------
        # 1. Cargar estudiantes y catálogo
        # ---------------------------------------------------------

        df_students_raw, df_courses_raw = load_data(current_file)

        df_students = df_students_raw.copy()

        df_students = df_students[
            df_students["curso_dentro_del_catalogo"] == "Sí"
        ].copy()

        df_students = add_convenio_activo(df_students)

        df_courses = df_courses_raw.copy()

        df_courses["vacantes_ofrecidas_maximas"] = pd.to_numeric(
            df_courses["vacantes_ofrecidas_maximas"],
            errors="coerce",
        )

        # En la primera iteración se guarda la cantidad original
        # de vacantes para mantener el tracking acumulado.
        if (
            iteration == 1
            or "vacantes_iniciales" not in df_courses.columns
        ):
            df_courses["vacantes_iniciales"] = (
                df_courses["vacantes_ofrecidas_maximas"]
            )

            df_courses["vacantes_usadas"] = 0

            df_courses["vacantes_restantes"] = (
                df_courses["vacantes_ofrecidas_maximas"]
            )

        # ---------------------------------------------------------
        # 2. Mejor combinación de K cursos por estudiante
        # ---------------------------------------------------------

        df_combos, df_best = generate_best_combos_per_student(
            df_students=df_students,
            df_courses=df_courses,
            k=k,
            schedule_columns=config["schedule_columns"],
            start_module=config["start_module"],
            end_module=config["end_module"],
            priority_values=config["priority_values"],
        )

        print(
            "[REAL] Estudiantes con combinación viable: "
            f"{df_best['RUT UC'].nunique()}"
        )

        if df_best.empty:
            print("[REAL] No hay combinaciones viables. Fin.")
            break

        # ---------------------------------------------------------
        # 3. Construcción y ordenamiento de la demanda
        # ---------------------------------------------------------

        df_demand = build_course_demand(df_best, k)

        df_demand = df_demand.merge(
            df_courses[
                ["nrc", "vacantes_ofrecidas_maximas"]
            ],
            left_on="NRC",
            right_on="nrc",
            how="left",
        ).drop(columns="nrc")

        df_sorted = sort_course_demand_like_original(df_demand)

        # ---------------------------------------------------------
        # 4. Asignación según vacantes disponibles
        # ---------------------------------------------------------

        df_assigned = assign_by_vacancies(
            df_sorted,
            df_courses,
        )

        df_assigned = df_assigned.sort_values(
            by="Nombre",
            key=lambda x: x.astype(str).str.lower(),
        )

        df_success, df_fail = split_success_fail(
            df_assigned,
            df_students_raw,
            k,
        )

        print(
            f"[REAL] Estudiantes con {k} cursos asignados: "
            f"{df_success['RUT UC'].nunique()}"
        )

        print(
            "[REAL] Estudiantes sin éxito: "
            f"{df_fail['RUT UC'].nunique()}"
        )

        # Guardar resultado de la iteración.
        if df_success.empty:
            print("[REAL] No hay más asignaciones exitosas.")
            break

        save_output(
            f"output_{iteration}.xlsx",
            df_success,
            df_fail,
            df_combos,
        )
        # ---------------------------------------------------------
        # 5. Actualizar vacantes acumuladas
        # ---------------------------------------------------------

        usados_por_nrc = (
            df_success["NRC"]
            .astype(str)
            .value_counts()
        )

        def update_row(row):
            """
            Actualiza el uso acumulado de vacantes para un curso.
            """
            inicial = pd.to_numeric(
                row["vacantes_iniciales"],
                errors="coerce",
            )

            usados_previos = pd.to_numeric(
                row["vacantes_usadas"],
                errors="coerce",
            )

            if pd.isna(usados_previos):
                usados_previos = 0

            usados_nuevos = usados_por_nrc.get(
                str(row["nrc"]),
                0,
            )

            usados_total = (
                usados_previos
                + usados_nuevos
            )

            restantes = (
                inicial - usados_total
                if pd.notna(inicial)
                else inicial
            )

            return pd.Series(
                {
                    "vacantes_iniciales": inicial,
                    "vacantes_usadas": usados_total,
                    "vacantes_restantes": restantes,
                    "vacantes_ofrecidas_maximas": restantes,
                }
            )

        df_courses[
            [
                "vacantes_iniciales",
                "vacantes_usadas",
                "vacantes_restantes",
                "vacantes_ofrecidas_maximas",
            ]
        ] = df_courses.apply(
            update_row,
            axis=1,
        )

        # ---------------------------------------------------------
        # 6. Crear formulario para la siguiente iteración
        # ---------------------------------------------------------

        fail_ruts = set(
            df_fail["RUT UC"].astype(str)
        )

        df_students_next = df_students_raw[
            df_students_raw["rut_uc"]
            .astype(str)
            .isin(fail_ruts)
        ]

        next_file = (
            f"formulario_limpio_{iteration + 1}.xlsx"
        )

        save_next_formulario(
            next_file,
            df_students_next,
            df_courses,
        )

        iteration += 1
        current_file = next_file

    print("\n[REAL] Proceso terminado.")


def run_single_course_fill(config):
    """
    Ejecuta la fase SINGLE.

    Utiliza las vacantes sobrantes después de la fase principal
    para intentar asignar un curso adicional por estudiante
    en cada ronda.

    La nueva asignación debe ser compatible con los cursos
    previamente obtenidos por el estudiante.
    """

    print(
        "\n[REAL – SINGLE] "
        "Inicio relleno de vacantes (1 curso)"
    )

    # -------------------------------------------------------------
    # 1. Detectar último estado de la fase principal
    # -------------------------------------------------------------

    last_output_k = find_last_file("output")
    last_form_k = find_last_file("formulario_limpio")

    if (
        last_output_k is None
        or last_form_k is None
    ):
        print(
            "[SINGLE] No se encontraron "
            "outputs/formularios de fase K."
        )
        return

    print(f"[SINGLE] Usando {last_output_k}")
    print(f"[SINGLE] Usando {last_form_k}")

    # Cursos previamente asignados.
    df_prev = pd.read_excel(
        last_output_k,
        sheet_name="Con éxito",
        dtype=str,
    )

    assigned_history = {
        str(rut): group["NRC"].astype(str).tolist()
        for rut, group in df_prev.groupby("RUT UC")
    }

    iteration = 1
    current_file = last_form_k

    # -------------------------------------------------------------
    # 2. Iteraciones SINGLE
    # -------------------------------------------------------------

    while os.path.exists(current_file):

        print(
            f"\n[SINGLE] Iteración {iteration} "
            f"| {current_file}"
        )

        df_students_raw, df_courses_raw = load_data(
            current_file
        )

        df_students = df_students_raw.copy()

        df_students = df_students[
            df_students["curso_dentro_del_catalogo"] == "Sí"
        ].copy()

        df_students = add_convenio_activo(
            df_students
        )

        df_courses = df_courses_raw.copy()

        df_courses["vacantes_ofrecidas_maximas"] = pd.to_numeric(
            df_courses["vacantes_ofrecidas_maximas"],
            errors="coerce",
        )

        # ---------------------------------------------------------
        # 3. Construir demanda de un curso
        # ---------------------------------------------------------

        df_demand = df_students[
            [
                "rut_uc",
                "nombre_completo",
                "nrc",
                "unidad_academica",
                "prioridad",
                "convenio_activo",
                "necesitas_este_curso_para_la_obtencion_del_grado_en_tu_universidad_de_origen",
            ]
        ].copy()

        df_demand.columns = [
            "RUT UC",
            "Nombre",
            "NRC",
            "Unidad Académica",
            "Prioridad",
            "Convenio",
            "ReqGrad",
        ]

        df_demand["Prioridad"] = pd.to_numeric(
            df_demand["Prioridad"],
            errors="coerce",
        )

        # Desempate aleatorio.
        df_demand["random_order"] = np.random.rand(
            len(df_demand)
        )

        # Se conserva exactamente el ordenamiento utilizado
        # actualmente por la fase SINGLE.
        df_sorted = df_demand.sort_values(
            by=[
                "NRC",
                "Prioridad",
                "Convenio",
                "ReqGrad",
                "random_order",
            ],
            ascending=[
                True,
                False,
                False,
                True,
                True,
            ],
        )

        # ---------------------------------------------------------
        # 4. Asignar máximo un curso por estudiante en esta ronda
        # ---------------------------------------------------------

        asignados = []
        asignados_ruts = set()

        vacantes = (
            df_courses
            .set_index(df_courses["nrc"].astype(str))[
                "vacantes_ofrecidas_maximas"
            ]
            .to_dict()
        )

        for _, row in df_sorted.iterrows():

            rut = str(row["RUT UC"])
            nrc = str(row["NRC"])

            # Máximo una asignación por estudiante
            # durante esta ronda.
            if rut in asignados_ruts:
                continue

            cupo = vacantes.get(
                nrc,
                np.nan,
            )

            if pd.isna(cupo) or cupo < 1:
                continue

            # Verificar compatibilidad con cursos
            # previamente asignados.
            prev_nrcs = assigned_history.get(
                rut,
                [],
            )

            candidate_nrcs = (
                prev_nrcs
                + [nrc]
            )

            course_rows = df_courses[
                df_courses["nrc"]
                .astype(str)
                .isin(candidate_nrcs)
            ]

            if not are_compatible_all(
                course_rows,
                config["schedule_columns"],
                config["start_module"],
                config["end_module"],
            ):
                continue

            # Asignar curso.
            vacantes[nrc] -= 1

            asignados_ruts.add(rut)
            asignados.append(row)

        if not asignados:
            print(
                "[SINGLE] No quedan asignaciones posibles."
            )
            break

        df_assigned = pd.DataFrame(
            asignados
        )

        df_assigned = df_assigned.sort_values(
            by="Nombre",
            key=lambda x: x.astype(str).str.lower(),
        )

        print(
            "[SINGLE] Estudiantes asignados "
            "en esta ronda: "
            f"{df_assigned['RUT UC'].nunique()}"
        )

        # ---------------------------------------------------------
        # 5. Guardar resultado SINGLE
        # ---------------------------------------------------------

        output_name = (
            f"output_single_{iteration}.xlsx"
        )

        with pd.ExcelWriter(output_name) as writer:

            df_assigned.to_excel(
                writer,
                sheet_name="Con éxito",
                index=False,
            )

            (
                df_students_raw[
                    ~df_students_raw["rut_uc"]
                    .astype(str)
                    .isin(asignados_ruts)
                ][
                    ["nombre_completo", "rut_uc"]
                ]
                .drop_duplicates()
                .to_excel(
                    writer,
                    sheet_name="Sin éxito",
                    index=False,
                )
            )

        print(
            f"[SINGLE] Guardado {output_name}"
        )

        # ---------------------------------------------------------
        # 6. Actualizar historial y vacantes
        # ---------------------------------------------------------

        for rut, group in df_assigned.groupby(
            "RUT UC"
        ):
            assigned_history.setdefault(
                str(rut),
                [],
            )

            assigned_history[str(rut)].extend(
                group["NRC"]
                .astype(str)
                .tolist()
            )

        for nrc, used in (
            df_assigned["NRC"]
            .astype(str)
            .value_counts()
            .items()
        ):
            df_courses.loc[
                df_courses["nrc"]
                .astype(str)
                == nrc,
                "vacantes_ofrecidas_maximas",
            ] -= used
        # ---------------------------------------------------------
        # 7. Crear siguiente formulario SINGLE
        # ---------------------------------------------------------

        next_file = (
            f"formulario_single_{iteration}.xlsx"
        )

        save_next_formulario(
            next_file,
            df_students_raw[
                ~df_students_raw["rut_uc"]
                .astype(str)
                .isin(asignados_ruts)
            ],
            df_courses,
        )

        iteration += 1
        current_file = next_file

    print(
        "\n[REAL – SINGLE] Relleno terminado."
    )