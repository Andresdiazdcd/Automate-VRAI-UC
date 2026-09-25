# asignacion.py

import numpy as np
import pandas as pd


def add_convenio_activo(df_students):
    """
    Agrega la columna 'convenio_activo'.

    Es True cuando:
    - ua_convenio == "General", o
    - unidad_academica == ua_convenio.
    """
    df = df_students.copy()
    df["convenio_activo"] = False

    general_mask = (
        df["ua_convenio"]
        .astype(str)
        .str.strip()
        .eq("General")
    )

    match_mask = (
        df["unidad_academica"]
        .astype(str)
        .str.strip()
        .eq(
            df["ua_convenio"]
            .astype(str)
            .str.strip()
        )
    )

    df.loc[
        general_mask | match_mask,
        "convenio_activo",
    ] = True

    return df


def build_course_demand(df_best, k):
    """
    Convierte la mejor combinación de cada estudiante
    en una fila por curso solicitado.
    """
    parts = []

    for i in range(1, k + 1):
        temp = df_best[
            [
                "RUT UC",
                "Nombre",
                f"Curso {i} - NRC",
                f"Curso {i} - Unidad Académica",
                f"Curso {i} - Prioridad",
                f"Curso {i} - Convenio",
                f"Curso {i} - ReqGrad",
            ]
        ].copy()

        temp.columns = [
            "RUT UC",
            "Nombre",
            "NRC",
            "Unidad Académica",
            "Prioridad",
            "Convenio",
            "ReqGrad",
        ]

        temp["Curso_num"] = i
        parts.append(temp)

    return pd.concat(parts, ignore_index=True)


def sort_course_demand_like_original(df_demand):
    """
    Ordena la demanda antes de repartir vacantes.
    """
    df = df_demand.copy()

    df["Prioridad"] = pd.to_numeric(
        df["Prioridad"],
        errors="coerce",
    )

    df["random_order"] = np.random.rand(len(df))

    return df.sort_values(
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
            False,
            True,
        ],
    )


def assign_by_vacancies(df_sorted, df_courses):
    """
    Asigna solicitudes mientras existan vacantes disponibles.
    """
    assigned_rows = []
    assigned_count = {}

    vacantes = (
        df_courses
        .set_index(df_courses["nrc"].astype(str))[
            "vacantes_ofrecidas_maximas"
        ]
        .to_dict()
    )

    for _, row in df_sorted.iterrows():
        nrc = str(row["NRC"])
        cap = vacantes.get(nrc, np.nan)

        if pd.isna(cap):
            continue

        used = assigned_count.get(nrc, 0)

        if used < cap:
            assigned_count[nrc] = used + 1
            assigned_rows.append(row)

    return pd.DataFrame(assigned_rows)


def split_success_fail(df_assigned, df_students_all, k):
    """
    Separa estudiantes con y sin éxito.

    Las columnas se renombran al guardar para mantener
    nombres legibles en los outputs.
    """
    if df_assigned.empty:
        df_fail = (
            df_students_all[
                ["nombre_completo", "rut_uc"]
            ]
            .drop_duplicates()
            .rename(
                columns={
                    "nombre_completo": "Nombre completo",
                    "rut_uc": "RUT UC",
                }
            )
        )

        return df_assigned, df_fail

    counts = df_assigned["RUT UC"].value_counts()

    success_ruts = (
        counts[counts >= k]
        .index
        .tolist()
    )

    df_success = df_assigned[
        df_assigned["RUT UC"].isin(success_ruts)
    ].copy()

    all_ruts = set(
        df_students_all["rut_uc"]
        .astype(str)
        .unique()
    )

    success_set = set(map(str, success_ruts))
    fail_ruts = list(all_ruts - success_set)

    df_fail = (
        df_students_all[
            df_students_all["rut_uc"]
            .astype(str)
            .isin(fail_ruts)
        ][
            ["nombre_completo", "rut_uc"]
        ]
        .drop_duplicates()
        .rename(
            columns={
                "nombre_completo": "Nombre completo",
                "rut_uc": "RUT UC",
            }
        )
        .copy()
    )

    return df_success, df_fail