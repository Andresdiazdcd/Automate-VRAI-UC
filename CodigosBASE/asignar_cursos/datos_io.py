# Funciones de lectura, escritura y búsqueda de archivos del proceso.

import os
import pandas as pd
import re
import unicodedata


def normalize_column_name(name):
    """
    Normaliza nombres de columnas:
    - minúsculas
    - sin tildes
    - espacios y símbolos -> "_"
    """
    name = str(name).strip().lower()

    name = unicodedata.normalize("NFKD", name)
    name = "".join(
        char for char in name
        if not unicodedata.combining(char)
    )

    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")

    return name


def normalize_columns(df):
    df = df.copy()
    df.columns = [
        normalize_column_name(col)
        for col in df.columns
    ]
    return df

def load_data(filename):
    df_students = pd.read_excel(
        filename,
        sheet_name="Cursos validados",
        dtype=str,
    )

    df_courses = pd.read_excel(
        filename,
        sheet_name="Catálogo VRAI",
        dtype=str,
    )

    df_students = normalize_columns(df_students)
    df_courses = normalize_columns(df_courses)

    return df_students, df_courses


def save_output(output_filename, df_success, df_fail, df_combinations):
    """
    Guarda los resultados de una iteración de la fase principal,
    ordenados alfabéticamente por nombre.
    """

    df_success = df_success.sort_values(
        by="Nombre",
        key=lambda x: x.astype(str).str.lower(),
    )

    df_fail = df_fail.sort_values(
        by="Nombre completo",
        key=lambda x: x.astype(str).str.lower(),
    )

    df_combinations = df_combinations.sort_values(
        by="Nombre",
        key=lambda x: x.astype(str).str.lower(),
    )

    with pd.ExcelWriter(output_filename) as writer:
        df_success.to_excel(
            writer,
            sheet_name="Con éxito",
            index=False,
        )

        df_fail.to_excel(
            writer,
            sheet_name="Sin éxito",
            index=False,
        )

        df_combinations.to_excel(
            writer,
            sheet_name="Posibles combinaciones",
            index=False,
        )


def save_next_formulario(next_filename, df_students, df_courses):
    """
    Guarda el formulario que será utilizado en la siguiente iteración.

    Contiene:
    - estudiantes que siguen en competencia;
    - catálogo actualizado con las vacantes restantes.
    """
    with pd.ExcelWriter(next_filename, engine="openpyxl") as writer:
        df_students.to_excel(
            writer,
            sheet_name="Cursos validados",
            index=False,
        )

        df_courses.to_excel(
            writer,
            sheet_name="Catálogo VRAI",
            index=False,
        )


def find_last_file(prefix, ext=".xlsx"):
    """
    Busca el último archivo consecutivo del tipo:

        prefix_1.xlsx
        prefix_2.xlsx
        prefix_3.xlsx
        ...

    Devuelve el último existente.
    """
    i = 1
    last = None

    while os.path.exists(f"{prefix}_{i}{ext}"):
        last = f"{prefix}_{i}{ext}"
        i += 1

    return last