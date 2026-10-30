import json
import os
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MODELO = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
API_KEY = os.getenv("GROQ_API_KEY")

with open(BASE_DIR / "data" / "juegos.json", encoding="utf-8") as archivo:
    JUEGOS = json.load(archivo)

cliente = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=API_KEY) if API_KEY else None

PALABRAS_VACIAS = {
    "que", "qué", "como", "cómo", "cual", "cuál", "cuales", "cuáles",
    "donde", "dónde", "cuando", "cuándo", "quien", "quién", "porque",
    "por", "para", "con", "sin", "los", "las", "del", "una", "unos",
    "unas", "este", "esta", "estos", "estas", "sobre", "hay", "fue",
    "son", "es", "mas", "más", "pero", "sus", "muy", "the", "and",
}

INSTRUCCIONES = (
    "Sos GameWiki IA, un asistente experto en videojuegos. "
    "Respondés siempre en español, de forma clara, breve y amable. "
    "Tenés que basarte ÚNICAMENTE en la información del contexto que se te "
    "proporciona, que proviene de los artículos de la wiki. "
    "Si la respuesta no está en el contexto, decilo honestamente y aclará "
    "que ese dato no figura en la wiki. No inventes datos ni fechas."
)


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

MAX_ITERACIONES_TOOL = 3


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", sin_tildes)


def texto_del_juego(juego):
    partes = [
        juego.get("titulo", ""),
        juego.get("genero", ""),
        str(juego.get("anio", "")),
        juego.get("desarrollador", ""),
        " ".join(juego.get("plataformas", [])),
        juego.get("descripcion", ""),
        juego.get("datos_curiosos", ""),
    ]
    return normalizar(" ".join(partes))


def buscar_juegos(pregunta, limite=4):
    palabras = {
        palabra
        for palabra in normalizar(pregunta)
        if len(palabra) > 2 and palabra not in PALABRAS_VACIAS
    }

    puntuados = []
    for juego in JUEGOS:
        contenido = set(texto_del_juego(juego))
        puntaje = len(palabras & contenido)
        puntuados.append((puntaje, juego))

    puntuados.sort(key=lambda par: par[0], reverse=True)
    return [juego for _, juego in puntuados[:limite]]


def construir_contexto(juegos):
    bloques = []
    for juego in juegos:
        bloques.append(
            f"### {juego['titulo']}\n"
            f"Género: {juego['genero']}\n"
            f"Año: {juego['anio']}\n"
            f"Desarrollador: {juego['desarrollador']}\n"
            f"Plataformas: {', '.join(juego['plataformas'])}\n"
            f"Descripción: {juego['descripcion']}\n"
            f"Datos curiosos: {juego['datos_curiosos']}"
        )
    return "\n\n".join(bloques)


def ejecutar_tool(nombre, argumentos):
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
                    "descripcion": juego.get("descripcion", ""),
                    "datos_curiosos": juego.get("datos_curiosos", ""),
                }
                for juego in juegos
            ],
        }
    return {"error": f"No se encontró la herramienta: {nombre}"}


def generar_respuesta(mensaje, historial):
    if cliente is None:
        raise RuntimeError(
            "Falta configurar GROQ_API_KEY. Copiá .env.example a .env "
            "y pegá tu clave de Groq."
        )

    contexto = construir_contexto(buscar_juegos(mensaje))
    sistema = f"{INSTRUCCIONES}\n\nContexto de la wiki:\n\n{contexto}"

    mensajes = [{"role": "system", "content": sistema}]
    for turno in historial[-10:]:
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

    while respuesta.choices and respuesta.choices[0].message.tool_calls:
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





app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html", juegos=JUEGOS)


@app.route("/api/chat", methods=["POST"])
def chat():
    datos = request.get_json(silent=True) or {}
    mensaje = str(datos.get("mensaje", "")).strip()
    historial = datos.get("historial", [])

    if not mensaje:
        return jsonify({"error": "Escribí una pregunta."}), 400
    if not isinstance(historial, list):
        historial = []

    try:
        respuesta = generar_respuesta(mensaje, historial)
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:
        mensajeError = f"Error al consultar la IA: {error}"
        estadoError = 502
        if "UNAVAILABLE" in str(error) or "503" in str(error):
            estadoError = 503
            mensajeError = "La IA está con alta demanda en este momento. Probá de nuevo en unos minutos."
        return jsonify({"error": mensajeError}), estadoError

    contenido, uso = generar_respuesta(mensaje, historial)
    return jsonify({
        "respuesta": contenido,
        "usage": uso,
    })


@app.route("/api/juegos")
def api_juegos():
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


if __name__ == "__main__":
    app.run(debug=True)
