==========================================================================
 EMAIL TRIAGE + EXTRACTION CON MODELOS DE LENGUAJE
 Proyecto - Curso de Modelos de Lenguaje
==========================================================================

1. DESCRIPCIÓN
--------------------------------------------------------------------------
Los equipos de finanzas y datos reciben muchas solicitudes por correo
(reportes, correcciones de datos, accesos, aprobaciones, análisis,
reuniones...). Este proyecto lee un correo y devuelve automáticamente:

  - Categoría de la solicitud (7 clases)
  - Urgencia (High / Medium / Low)
  - Resumen en una oración
  - Lista de tareas que pide el remitente
  - Campos clave: solicitante, fecha límite, montos e IDs de referencia
    (PO-, CC-, REQ-)

Todo se presenta en una interfaz gráfica hecha con Gradio, con dos modos:
un correo a la vez, o una "bandeja" completa (CSV) ordenada por urgencia.

No se entrena ningún modelo: se usan modelos de lenguaje preentrenados
pequeños y públicos de Hugging Face.


2. ENFOQUE / MODELOS
--------------------------------------------------------------------------
  Tarea                      Método
  -------------------------  ---------------------------------------------
  Categoría                  Clasificación zero-shot con un modelo NLI
                             (facebook/bart-large-mnli). Para cada categoría
                             el modelo evalúa la hipótesis "This email is
                             <descripción de la categoría>." y se elige la
                             de mayor probabilidad.
  Urgencia                   Mismo modelo zero-shot con 3 descripciones.
                             Modo "hybrid" (por defecto): si el correo trae
                             una señal explícita (ASAP, EOD today, by Friday,
                             no rush...) las reglas deciden; si no, decide
                             el modelo. Se reportan ambos resultados.
  Resumen                    google/flan-t5-base (modelo instruccional
                             seq2seq) con el prompt "Summarize this email
                             in one sentence."
  Tareas                     flan-t5-base con el prompt "What does the
                             sender ask the recipient to do? List the
                             actions."
  Solicitante, fecha,        Reglas (expresiones regulares) en
  montos, IDs                extractors.py

Los modelos se descargan solos de Hugging Face la primera vez (~2 GB).


3. ESTRUCTURA DEL REPOSITORIO
--------------------------------------------------------------------------
  email-triage-llm/
  ├── readme.txt                  <- este archivo
  ├── requirements.txt            <- dependencias de Python
  ├── email_triage_colab.ipynb    <- notebook para correr todo en Colab
  ├── data/
  │   ├── emails.csv              <- 140 correos sintéticos etiquetados
  │   └── emails_handwritten.csv  <- 21 correos escritos a mano (test difícil)
  ├── generate_data.py            <- genera data/emails.csv
  ├── make_handwritten.py         <- genera data/emails_handwritten.csv
  ├── extractors.py               <- extracción por reglas
  ├── triage.py                   <- sistema principal (modelos + reglas)
  ├── evaluate.py                 <- métricas y matrices de confusión
  ├── app.py                      <- interfaz gráfica (Gradio)
  └── results/                    <- se crea al correr evaluate.py


4. DATASET
--------------------------------------------------------------------------
Es un dataset PROPIO y viene incluido en la carpeta data/ del repositorio,
no hay que descargar nada.

  data/emails.csv  - 140 correos en inglés generados con plantillas
     (generate_data.py, semilla 42): 20 por categoría, con remitentes,
     montos, IDs y plazos aleatorios.
  data/emails_handwritten.csv - 21 correos escritos a mano (3 por
     categoría) con redacción más informal y variada, para probar el
     sistema en condiciones menos "perfectas".

Columnas: email_id, email_text, category, urgency, requester, due_date,
amounts, ids (y tasks en el sintético). Los valores múltiples van
separados por ";".

Categorías: Report Request, Data Correction, Access Request, Approval
Request, Ad-hoc Analysis, Meeting Request, FYI / No Action.

Si se borran, se regeneran idénticos con:
    python generate_data.py
    python make_handwritten.py
y quedan guardados en data/ (el código los busca ahí).


5. CÓMO REPLICAR LOS EXPERIMENTOS
--------------------------------------------------------------------------
OPCIÓN A - Google Colab (recomendada, no requiere instalar nada)

  1. Abrir https://colab.research.google.com
  2. Archivo -> Abrir cuaderno -> pestaña GitHub -> pegar la URL de este
     repositorio -> abrir email_triage_colab.ipynb
  3. Entorno de ejecución -> Cambiar tipo de entorno -> GPU (T4)
     (opcional; en CPU funciona pero es más lento)
  4. La primera celda clona el repositorio
     (https://github.com/mlau1818/email-triage-llm) e instala todo.
  5. Ejecutar las celdas en orden:
       - instala dependencias
       - (opcional) regenera los datos
       - prueba un correo desde Python
       - corre la evaluación y muestra métricas y matrices de confusión
       - lanza la interfaz: abrir el enlace https://xxxx.gradio.live

OPCIÓN B - Local (Python 3.10 o superior)

  1. Clonar el repositorio:
       git clone https://github.com/mlau1818/email-triage-llm.git
       cd email-triage-llm
  2. (Recomendado) crear un entorno virtual:
       python -m venv .venv
       Windows:     .venv\Scripts\activate
       Mac/Linux:   source .venv/bin/activate
  3. Instalar dependencias:
       pip install -r requirements.txt
  4. Correr la evaluación (desde la carpeta raíz del proyecto):
       python evaluate.py
     Opcional, prueba rápida con pocos correos:
       python evaluate.py --limit 20
  5. Abrir la interfaz:
       python app.py
     y entrar a http://127.0.0.1:7860 en el navegador.

Tiempo aproximado: la primera ejecución descarga los modelos (2-5 min).
La evaluación completa (161 correos) tarda ~1-2 min con GPU y ~10-15 min
en CPU.


6. RESULTADOS (salidas de evaluate.py)
--------------------------------------------------------------------------
Se guardan en results/:
  - metrics.json: accuracy y F1 macro de categoría, accuracy de urgencia
    (modelo solo vs. híbrido) y exact match de solicitante, fecha límite,
    montos e IDs, para cada dataset.
  - predictions_<dataset>.csv: predicción vs. etiqueta para cada correo,
    con resumen y tareas generadas.
  - confusion_<dataset>.png: matriz de confusión de categorías.

Nota: el dataset sintético es muy regular, por eso las reglas de
extracción aciertan prácticamente todo ahí; el dataset escrito a mano es
la prueba más realista. La comparación "urgencia modelo solo vs. híbrido"
muestra cuánto aporta combinar el modelo con reglas simples.


7. USO DE LA INTERFAZ
--------------------------------------------------------------------------
  Pestaña "Single email": pegar un correo (o elegir un ejemplo del
  desplegable) y presionar Analyze. Muestra urgencia, top-3 categorías con
  probabilidad, resumen, tareas y tabla de campos extraídos.

  Pestaña "Inbox (CSV)": subir un CSV con una columna email_text (o dejarlo
  vacío para usar los 21 ejemplos). Devuelve la bandeja ordenada por
  urgencia y un CSV descargable con los resultados.


8. LIMITACIONES
--------------------------------------------------------------------------
  - Los correos son sintéticos y en inglés; con correos reales el
    desempeño puede variar.
  - El zero-shot depende mucho de cómo se redactan las descripciones de
    las categorías (CATEGORY_DESCRIPTIONS en triage.py).
  - flan-t5-base es un modelo pequeño: los resúmenes y tareas pueden ser
    genéricos o incompletos en correos largos. Se puede cambiar a
    google/flan-t5-large en GEN_MODEL (más lento, mejor calidad).
  - Las fechas se extraen como texto ("Friday", "EOD today"), no se
    convierten a una fecha de calendario.
