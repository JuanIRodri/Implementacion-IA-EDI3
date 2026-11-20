# Librerias estandar
import json
import os
import pickle
import re
import unicodedata
from pathlib import Path

# Librerias de la aplicacion
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

# Libreria de embeddings (opcional, se usa sentence-transformers)
try:
    from sentence_transformers import SentenceTransformer
    DISPONIBLE_EMBEDDINGS = True
except ImportError:
    SentenceTransformer = None
    DISPONIBLE_EMBEDDINGS = False

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Configuracion del servidor Flask
BASE_DIR = Path(__file__).resolve().parent
# Configuracion del modelo de Groq
MODELO = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
# API key de Groq
API_KEY = os.getenv("GROQ_API_KEY")
# Configuracion del modelo de embeddings
MODELO_EMBEDDINGS = os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")
# Archivo donde se guarda el cache de embeddings
CACHE_EMBEDDINGS = BASE_DIR / "data" / "embeddings_cache.pkl"
# Similitud minima para considerar un juego como candidato
UMBRAL_SIMILARIDAD = 0.35

# Carga los juegos desde el archivo JSON de la wiki
with open(BASE_DIR / "data" / "juegos.json", encoding="utf-8") as archivo:
    JUEGOS = json.load(archivo)

# Cliente de la API de Groq (OpenAI SDK)
cliente = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=API_KEY) if API_KEY else None

# Estado del modelo y los vectores de embeddings
modelo_embeddings = None
vectores_embeddings = None

# Palabras vacias comunes que se ignoran al buscar
PALABRAS_VACIAS = {
    "que", "qué", "como", "cómo", "cual", "cuál", "cuales", "cuáles",
    "donde", "dónde", "cuando", "cuándo", "quien", "quién", "porque",
    "por", "para", "con", "sin", "los", "las", "del", "una", "unos",
    "unas", "este", "esta", "estos", "estas", "sobre", "hay", "fue",
    "son", "es", "mas", "más", "pero", "sus", "muy", "the", "and",
}

# Alias de juegos (abreviaturas) -> nombre completo
ALIAS = {
    "hk": "hollow knight",
    "gta": "grand theft auto",
    "lol": "league of legends",
    "wow": "world of warcraft",
    "mc": "minecraft",
    "zelda": "zelda",
    "mario": "mario",
    "tarkov": "escape from tarkov",
    "witcher": "witcher",
    "dark souls": "dark souls",
    "among us": "among us",
    "ark": "ark",
    "arena": "arena break out infinite",
}

# Instrucciones del sistema para el asistente
INSTRUCCIONES = (
    "Sos GameWiki IA, un asistente experto en videojuegos. "
    "Respondés siempre en español, de forma clara, breve y amable. "
    "Tenés que basarte ÚNICAMENTE en la información del contexto que se te "
    "proporciona, que proviene de los artículos de la wiki. "
    "Si la respuesta no está en el contexto, decilo honestamente y aclará "
    "que ese dato no figura en la wiki. No inventes datos ni fechas."
)


# Declaracion de la tool (function calling) que usa el modelo
DECLARACION_TOOL = {
    "type": "function",
    "function": {
        "name": "buscar_juegos",
        "description": (
            "Busca en la wiki de videojuegos los artículos más relevantes para una "
            "consulta y devuelve sus datos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Consulta del usuario: título, género o palabra clave.",
                },
            },
            "required": ["consulta"],
        },
    },
}

# Cantidad maxima de iteraciones de tool calling
MAX_ITERACIONES_TOOL = 10


def normalizar(texto):
    """Convierte un texto en minusculas, sin tildes y devuelve los tokens alfanumericos.

    Args:
        texto: Texto de entrada.

    Returns:
        Lista de palabras en minusculas sin tildes ni caracteres no alfanumericos.
    """
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", sin_tildes)


def texto_del_juego(juego):
    """Arma el texto descriptivo del juego a partir de sus campos (titulo, genero, anio, etc.).

    Args:
        juego: Diccionario con los datos del juego.

    Returns:
        Texto normalizado con la informacion del juego.
    """
    partes = [
        juego.get("titulo", ""),
        juego.get("genero", ""),
        str(juego.get("anio", "")),
        juego.get("desarrollador", ""),
        " ".join(juego.get("plataformas", [])),
        juego.get("descripcion", ""),
        juego.get("datos_curiosos", ""),
        juego.get("clasificacion", ""),
        " ".join(juego.get("tags", [])),
    ]
    return normalizar(" ".join(partes))


def _modelo_o_nativo():
    """Carga el modelo de embeddings (sentence-transformers) y devuelve el modelo.

    Returns:
        El modelo cargado o None si no esta disponible.
    """
    global modelo_embeddings
    if modelo_embeddings is None and DISPONIBLE_EMBEDDINGS:
        try:
            modelo_embeddings = SentenceTransformer(MODELO_EMBEDDINGS)
        except Exception:
            modelo_embeddings = None
    return modelo_embeddings


def _cargar_o_generar_vectores(modelo):
    """Genera los embeddings de los juegos o carga el cache guardado.

    Args:
        modelo: Modelo de embeddings para generar los vectores.

    Returns:
        Lista de vectores de embeddings de los juegos.
    """
    global vectores_embeddings
    vectores = None
    if CACHE_EMBEDDINGS.exists():
        try:
            with open(CACHE_EMBEDDINGS, "rb") as archivo:
                guardados = pickle.load(archivo)
            if len(guardados) == len(JUEGOS):
                vectores = [list(map(float, vector)) for vector in guardados]
        except Exception:
            vectores = None
    if vectores is None:
        textos = [" ".join(texto_del_juego(juego)) for juego in JUEGOS]
        generados = modelo.encode(inputs=textos)
        vectores = [list(map(float, vector)) for vector in generados]
        try:
            with open(CACHE_EMBEDDINGS, "wb") as archivo:
                pickle.dump(vectores, archivo)
        except Exception:
            pass
    vectores_embeddings = vectores
    return vectores


def _vectores_juegos():
    """Devuelve los vectores de embeddings de los juegos, generandolos si es necesario.

    Returns:
        Lista de vectores de embeddings o None si no hay modelo disponible.
    """
    global vectores_embeddings
    modelo = _modelo_o_nativo()
    if modelo is None:
        return None
    if vectores_embeddings is None:
        vectores_embeddings = _cargar_o_generar_vectores(modelo)
    return vectores_embeddings


def similitud_coseno(a, b):
    """Calcula la similitud coseno entre dos vectores.

    Args:
        a: Primer vector de embeddings.
        b: Segundo vector de embeddings.

    Returns:
        Similitud entre ambos vectores o 0.0 si alguno es None.
    """
    if a is None or b is None:
        return 0.0
    producto = sum(x * y for x, y in zip(a, b))
    norma_a = sum(x * x for x in a) ** 0.5
    norma_b = sum(x * x for x in b) ** 0.5
    denominador = norma_a * norma_b
    if denominador == 0:
        return 0.0
    return producto / denominador


def _similitudes_consulta(consulta):
    """Calcula la similitud entre la consulta y los juegos.

    Args:
        consulta: Consulta del usuario normalizada.

    Returns:
        Similitudes por juego o None si no hay modelo disponible.
    """
    modelo = _modelo_o_nativo()
    if modelo is None:
        return None
    vector = modelo.encode(inputs=[" ".join(normalizar(consulta))])
    vectores = _vectores_juegos()
    if vectores is None:
        return None
    similitudes = {}
    for juego, vector_juego in zip(JUEGOS, vectores):
        similitudes[juego.get("id", "")] = similitud_coseno(vector[0], vector_juego)
    return similitudes


def buscar_juegos(pregunta, limite=8, min_puntaje=1):
    """Busca juegos usando coincidencia de palabras y embeddings.

    Args:
        pregunta: Pregunta o consulta del usuario.
        limite: Cantidad maxima de juegos a devolver.
        min_puntaje: Puntaje minimo para considerar un juego candidato.

    Returns:
        Lista de juegos encontrados ordenados por puntaje.
    """
    consulta = pregunta.lower()
    for alias, termino in ALIAS.items():
        consulta = consulta.replace(alias, termino)
    palabras = {
        palabra
        for palabra in normalizar(consulta)
        if len(palabra) > 2 and palabra not in PALABRAS_VACIAS
    }

    generos_disponibles = [
        set(normalizar(juego.get("genero", ""))) for juego in JUEGOS
    ]
    coincide_genero = any(
        palabras & genero for genero in generos_disponibles if genero
    )

    similitudes = _similitudes_consulta(consulta)

    puntuados = []
    for juego, juego_generos in zip(JUEGOS, generos_disponibles):
        contenido = set(texto_del_juego(juego))
        puntaje = len(palabras & contenido)
        if coincide_genero and palabras & juego_generos:
            puntaje += 3
        sim = similitudes.get(juego.get("id", ""), 0.0) if similitudes is not None else 0.0
        puntuados.append((puntaje, juego, sim))

    resultados = []
    for puntaje, juego, sim in puntuados:
        score = puntaje + sim
        es_valido = (
            puntaje >= min_puntaje
            or (similitudes is not None and sim >= UMBRAL_SIMILARIDAD)
        )
        if not es_valido:
            continue
        resultados.append((score, juego))

    resultados.sort(key=lambda par: par[0], reverse=True)
    return [juego for _, juego in resultados[:limite]]


# Conectores comunes que indican que la consulta es una continuación del contexto.
CONECTORES_CONTINUACION = {
    "y", "tambien", "también", "ese", "esa", "aquel", "aquella",
    "este", "esta", "estos", "estas", "lo mismo", "igualmente",
    "de ese", "de esa", "de aquel", "de aquella", "de este", "de esta",
}


def historial_usuarios(historial):
    """Devuelve los contenidos de los turnos del usuario.

    Args:
        historial: Lista de turnos de la conversacion.

    Returns:
        Lista de textos de las consultas del usuario.
    """
    return [
        str(turno.get("content", "")).strip()
        for turno in historial
        if turno.get("role") == "user" and str(turno.get("content", "")).strip()
    ]


def expandir_consulta(mensaje, historial):
    """Si la consulta es una continuacion, agrega el historial previo.

    Args:
        mensaje: Mensaje del usuario.
        historial: Historial de la conversacion.

    Returns:
        Consulta ampliada con el contexto previo si corresponde.
    """
    palabras = normalizar(mensaje)
    es_continuacion = (
        len(palabras) <= 3
        or (palabras and palabras[0] in CONECTORES_CONTINUACION)
        or any(
            c in mensaje.lower()
            for c in ["y ", "también ", "tambien ", "ese ", "esa ", "aquel ", "este ", "esta "]
        )
    )
    if es_continuacion and historial:
        previos = historial_usuarios(historial)
        if previos:
            return f"{previos[-1]} {mensaje}"
    return mensaje


def construir_contexto(juegos):
    """Arma el contexto de la wiki con los datos de los juegos encontrados.

    Args:
        juegos: Lista de juegos encontrados.

    Returns:
        Texto con el contexto de los juegos para el modelo.
    """
    bloques = []
    for juego in juegos:
        bloques.append(
            f"### {juego['titulo']}\n"
            f"Género: {juego['genero']}\n"
            f"Año: {juego['anio']}\n"
            f"Desarrollador: {juego['desarrollador']}\n"
            f"Plataformas: {', '.join(juego['plataformas'])}\n"
            f"Clasificación: {juego.get('clasificacion', '–')}\n"
            f"Precio: {juego.get('precio', '–')}\n"
            f"Jugadores: {juego.get('jugadores', '–')}\n"
            f"Duración: {juego.get('duracion', '–')}\n"
            f"Puntuación: {juego.get('puntuacion', '–')}\n"
            f"Etiquetas: {', '.join(juego.get('tags', []))}\n"
            f"Descripción: {juego['descripcion']}"
        )
    return "\n\n".join(bloques)


def ejecutar_tool(nombre, argumentos):
    """Ejecuta la tool del modelo (por ahora buscar_juegos).

    Args:
        nombre: Nombre de la tool a ejecutar.
        argumentos: Argumentos con la consulta de la tool.

    Returns:
        Resultado de la busqueda con los juegos encontrados.
    """
    if nombre == "buscar_juegos":
        juegos = buscar_juegos(str(argumentos.get("consulta", "")), limite=4)
        return {
            "juegos_encontrados": len(juegos),
            "resultados": [
                {
                    "titulo": juego.get("titulo", ""),
                    "genero": juego.get("genero", ""),
                    "anio": juego.get("anio", ""),
                    "desarrollador": juego.get("desarrollador", ""),
                    "plataformas": juego.get("plataformas", []),
                    "clasificacion": juego.get("clasificacion", ""),
                    "precio": juego.get("precio", ""),
                    "jugadores": juego.get("jugadores", ""),
                    "motor": juego.get("motor", ""),
                    "duracion": juego.get("duracion", ""),
                    "puntuacion": juego.get("puntuacion", ""),
                    "tags": juego.get("tags", []),
                    "enlace": juego.get("enlace", ""),
                    "descripcion": juego.get("descripcion", ""),
                    "datos_curiosos": juego.get("datos_curiosos", ""),
                }
                for juego in juegos
            ],
        }
    return {"error": f"No se encontró la herramienta: {nombre}"}


def generar_respuesta(mensaje, historial):
    """Genera la respuesta del asistente usando Groq con function calling.

    Args:
        mensaje: Mensaje del usuario.
        historial: Historial de la conversacion.

    Returns:
        Tupla con el contenido de la respuesta y el uso de tokens de la API.
    """
    if cliente is None:
        raise RuntimeError(
            "Falta configurar GROQ_API_KEY. Copiá .env.example a .env "
            "y pegá tu clave de Groq."
        )

    consulta = expandir_consulta(mensaje, historial)
    contexto = construir_contexto(buscar_juegos(consulta))
    sistema = f"{INSTRUCCIONES}\n\nContexto de la wiki:\n\n{contexto}"

    mensajes = [{"role": "system", "content": sistema}]
    for turno in historial[-6:]:
        texto = str(turno.get("content", "")).strip()
        if not texto:
            continue
        rol = "user" if turno.get("role") == "user" else "assistant"
        mensajes.append({"role": rol, "content": texto})
    mensajes.append({"role": "user", "content": mensaje})

    def crear_config():
        return {
            "model": MODELO,
            "messages": mensajes,
            "temperature": 0.4,
            "tools": [DECLARACION_TOOL],
        }

    respuesta = cliente.chat.completions.create(**crear_config())

    iteraciones = 0
    while (
        respuesta.choices
        and respuesta.choices[0].message.tool_calls
        and iteraciones < MAX_ITERACIONES_TOOL
    ):
        iteraciones += 1
        mensaje_ia = respuesta.choices[0].message
        tool_calls = mensaje_ia.tool_calls or []
        mensajes.append(
            {
                "role": "assistant",
                "content": mensaje_ia.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            if tc.function.name == "buscar_juegos":
                argumentos = json.loads(tc.function.arguments or "{}")
                consulta_tool = expandir_consulta(
                    str(argumentos.get("consulta", "")), historial + [{"role": "user", "content": mensaje}]
                )
                argumentos["consulta"] = consulta_tool
                resultado = ejecutar_tool("buscar_juegos", argumentos)
                mensajes.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(resultado),
                    }
                )
        respuesta = cliente.chat.completions.create(**crear_config())

    return respuesta.choices[0].message.content, {
        "prompt_tokens": respuesta.usage.prompt_tokens if respuesta.usage else None,
        "completion_tokens": respuesta.usage.completion_tokens if respuesta.usage else None,
        "total_tokens": respuesta.usage.total_tokens if respuesta.usage else None,
    }





# Instancia de la aplicacion Flask
app = Flask(__name__)


# Ruta principal de la web
@app.route("/")
def inicio():
    # Sirve la pagina principal con la lista de juegos y el chat.
    return render_template("index.html", juegos=JUEGOS)


# Endpoint del chat
@app.route("/api/chat", methods=["POST"])
def chat():
    # Endpoint del chat: recibe el mensaje y el historial y devuelve la respuesta.
    datos = request.get_json(silent=True) or {}
    mensaje = str(datos.get("mensaje", "")).strip()
    historial = datos.get("historial", [])

    if not mensaje:
        return jsonify({"error": "Escribí una pregunta."}), 400
    if not isinstance(historial, list):
        historial = []

    try:
        contenido, uso = generar_respuesta(mensaje, historial)
    except RuntimeError as error:
        # Error de configuracion: falta la API key de Groq
        return jsonify({"error": str(error)}), 503
    except Exception as error:
        # Error general al consultar la IA
        mensajeError = f"Error al consultar la IA: {error}"
        estadoError = 502
        if "UNAVAILABLE" in str(error) or "503" in str(error):
            estadoError = 503
            mensajeError = "La IA está con alta demanda en este momento. Probá de nuevo en unos minutos."
        return jsonify({"error": mensajeError}), estadoError

    return jsonify({
        "respuesta": contenido,
        "usage": uso,
    })


# Endpoint que lista los juegos de la wiki
@app.route("/api/juegos")
def api_juegos():
    # Endpoint que lista los juegos de la wiki con paginacion.
    pagina = max(1, request.args.get("page", 1, type=int))
    por_pagina = min(max(1, request.args.get("por_pagina", 6, type=int)), 48)
    inicio = (pagina - 1) * por_pagina
    fin = inicio + por_pagina
    juegos_paginados = JUEGOS[inicio:fin]
    total_paginas = max(1, (len(JUEGOS) + por_pagina - 1) // por_pagina)
    return jsonify({
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": len(JUEGOS),
        "total_paginas": total_paginas,
        "juegos": juegos_paginados,
    })


# Punto de entrada del script: arranca el servidor de desarrollo
if __name__ == "__main__":
    app.run(debug=True)
