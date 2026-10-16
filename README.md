# Asignación de cursos de intercambio

Proyecto para asignar cursos a estudiantes de intercambio considerando prioridades, compatibilidad horaria, campus y disponibilidad de vacantes.

El proceso se divide en dos etapas:

1. **Fase principal:** intenta asignar `K` cursos a cada estudiante.
2. **Fase SINGLE:** utiliza las vacantes restantes para asignar cursos adicionales, de uno en uno.

---

## Estructura del proyecto

```text
proyecto/
│
├── main.ipynb
├── config.py
├── datos_io.py
├── horarios.py
├── combinaciones.py
├── asignacion.py
├── iteraciones.py
└── README.md
```

### `main.ipynb`

Notebook utilizado para ejecutar el algoritmo.

Desde aquí se indican los parámetros propios de cada ejecución, como:

- archivo inicial;
- cantidad `K` de cursos de la fase principal;
- archivos desde los cuales comenzar la fase SINGLE.

### `config.py`

Contiene parámetros generales del algoritmo que normalmente no cambian entre ejecuciones:

- puntajes asociados a las prioridades;
- equivalencia entre horarios y módulos;
- columnas del catálogo que contienen información horaria.

### `datos_io.py`

Contiene las funciones relacionadas con:

- lectura de archivos Excel;
- normalización de nombres de columnas;
- guardado de resultados;
- creación de formularios para las siguientes iteraciones.

### `horarios.py`

Contiene la lógica de compatibilidad técnica entre cursos.

Una combinación se considera incompatible cuando:

- dos cursos ocupan el mismo módulo el mismo día;
- dos cursos están en campus distintos y tienen módulos consecutivos.

### `combinaciones.py`

Genera todas las combinaciones posibles de `K` cursos para cada estudiante.

Se descartan combinaciones que:

- repitan una misma sigla;
- contengan NRC que no estén presentes en el catálogo;
- tengan conflictos de horario o campus.

Cada combinación válida recibe un puntaje según las prioridades de los cursos y se selecciona aquella con mayor puntaje.

### `asignacion.py`

Contiene funciones relacionadas con:

- identificación de convenio activo;
- construcción de la demanda;
- ordenamiento de solicitudes;
- asignación según vacantes;
- separación entre estudiantes con y sin éxito.

### `iteraciones.py`

Contiene los dos procesos principales:

```python
run_iterations_real()
run_single_course_fill()
```

---

# Datos de entrada

El archivo inicial debe contener al menos las hojas:

## `Cursos validados`

Cada fila corresponde a un curso solicitado por un estudiante.

Un mismo estudiante puede aparecer en varias filas.

Solo se consideran solicitudes donde:

```text
Curso dentro del catálogo = Sí
```

## `Catálogo VRAI`

Contiene la información de los cursos, incluyendo:

- NRC;
- sigla;
- campus;
- horarios;
- vacantes ofrecidas.

---

# Normalización de columnas

Al cargar los archivos Excel, los nombres de las columnas se normalizan automáticamente para reducir errores producidos por diferencias de formato.

La normalización:

- convierte los nombres a minúsculas;
- elimina tildes;
- elimina espacios iniciales y finales;
- reemplaza espacios y caracteres especiales por `_`.

Por ejemplo:

```text
RUT UC                       -> rut_uc
NRC                          -> nrc
Unidad Académica             -> unidad_academica
Horario Cátedra              -> horario_catedra
Vacantes Ofrecidas Máximas   -> vacantes_ofrecidas_maximas
```

La normalización afecta únicamente a los nombres de las columnas, no al contenido de los datos.

Internamente, los DataFrames cargados desde Excel utilizan estos nombres normalizados.

Las tablas creadas por el algoritmo y los archivos de salida mantienen nombres más legibles, como:

```text
RUT UC
NRC
Nombre
Prioridad
Convenio
ReqGrad
```

---

# Fase principal: asignación de K cursos

La fase principal se ejecuta desde el notebook indicando el archivo inicial y la cantidad de cursos a asignar:

```python
run_iterations_real(
    CONFIG,
    start_file="formulario_limpio_1.xlsx",
    k_courses=2,
)
```

Para cada estudiante:

1. Se consideran sus solicitudes que pertenecen al catálogo.
2. Se generan todas las combinaciones posibles de tamaño `K`.
3. Se eliminan combinaciones con siglas repetidas.
4. Se verifica que todos los NRC existan en el catálogo.
5. Se verifica compatibilidad de horario y campus.
6. Se calcula un puntaje total según las prioridades.
7. Se selecciona la combinación con mayor puntaje.

La combinación seleccionada representa los cursos por los cuales el estudiante compite en esa iteración.

---

## Ordenamiento de la demanda

Las solicitudes se agrupan por NRC y se ordenan considerando:

1. prioridad;
2. convenio;
3. necesidad del curso para la obtención del grado;
4. orden aleatorio como mecanismo de desempate.

Luego se recorren las solicitudes respetando las vacantes disponibles.

---

## Éxito de un estudiante

Un estudiante tiene éxito en una iteración cuando obtiene al menos `K` cursos.

Los estudiantes exitosos salen del proceso principal.

Los estudiantes que no alcanzan `K` cursos pasan a la siguiente iteración.

---

## Actualización de vacantes

Después de cada iteración se mantiene el seguimiento de:

```text
vacantes_iniciales
vacantes_usadas
vacantes_restantes
vacantes_ofrecidas_maximas
```

Las vacantes disponibles para la siguiente ronda corresponden a las vacantes restantes.

---

## Archivos generados

Cada iteración exitosa genera:

```text
output_1.xlsx
output_2.xlsx
...
```

Cada `output` contiene:

- `Con éxito`;
- `Sin éxito`;
- `Posibles combinaciones`.

Las tablas se guardan ordenadas alfabéticamente por nombre.

Si una iteración no produce estudiantes exitosos, no se genera un `output` vacío.

También se generan nuevos formularios:

```text
formulario_limpio_2.xlsx
formulario_limpio_3.xlsx
...
```

Estos contienen:

- los estudiantes que continúan en competencia;
- el catálogo actualizado con las vacantes restantes.

---

# Fase SINGLE

Una vez terminada la fase principal, puede ejecutarse una segunda etapa para utilizar las vacantes sobrantes.

La fase SINGLE intenta asignar como máximo un curso adicional por estudiante en cada ronda.

Se ejecuta indicando explícitamente el último resultado y formulario de la fase principal:

```python
run_single_course_fill(
    CONFIG,
    last_output_k="output_3.xlsx",
    last_form_k="formulario_limpio_4.xlsx",
)
```

Los nombres utilizados deben corresponder al último estado válido generado por la fase principal.

---

## Funcionamiento de SINGLE

En cada iteración:

1. Se consideran nuevamente las solicitudes de los estudiantes restantes.
2. Se ordenan según prioridad, convenio, necesidad de grado y desempate aleatorio.
3. Se intenta asignar como máximo un curso por estudiante.
4. Se verifica que el nuevo curso sea compatible con los cursos previamente asignados.
5. Se descuenta la vacante utilizada.
6. Se actualiza el historial de cursos asignados.
7. Se crea el formulario para la siguiente ronda.

El proceso termina cuando no quedan nuevas asignaciones posibles.

Los resultados se guardan como:

```text
output_single_1.xlsx
output_single_2.xlsx
...
```

---

# Ejecución desde `main.ipynb`

Importar configuración y funciones:

```python
from config import CONFIG
from iteraciones import (
    run_iterations_real,
    run_single_course_fill,
)
```

Ejecutar la fase principal:

```python
run_iterations_real(
    CONFIG,
    start_file="formulario_limpio_1.xlsx",
    k_courses=2,
)
```

Opcionalmente, ejecutar después la fase SINGLE:

```python
run_single_course_fill(
    CONFIG,
    last_output_k="output_3.xlsx",
    last_form_k="formulario_limpio_4.xlsx",
)
```

La configuración general permanece en `config.py`, mientras que los parámetros propios de cada ejecución se indican directamente desde el notebook.