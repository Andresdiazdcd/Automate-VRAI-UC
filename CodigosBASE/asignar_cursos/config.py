# Configuración general del proceso de asignación de cursos.

CONFIG = {
    # Puntaje asociado a cada prioridad.
    # Se utiliza para elegir la mejor combinación de cursos por estudiante.
    "priority_values": {
        1: 150,
        2: 130,
        3: 110,
        4: 100,
        5: 70,
        6: 60,
        7: 50,
        8: 40,
        9: 30,
        10: 20,
    },

    # Conversión de horarios reales a módulos UC.
    "start_module": {
        "0820": 1,
        "0940": 2,
        "1100": 3,
        "1220": 4,
        "1450": 5,
        "1610": 6,
        "1730": 7,
        "1850": 8,
        "2010": 9,
    },

    "end_module": {
        "0930": 1,
        "1050": 2,
        "1210": 3,
        "1330": 4,
        "1600": 5,
        "1720": 6,
        "1840": 7,
        "2000": 8,
        "2120": 9,
    },

    # Columnas del catálogo donde pueden aparecer bloques horarios.
    "schedule_columns": [
        "horario_catedra",
        "horario_ayudantia",
        "horario_taller",
        "horario_laboratorio",
    ],
}