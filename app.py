import json
import os
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MODELO = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.getenv("GEMINI_API_KEY")

with open(BASE_DIR / "data" / "juegos.json", encoding="utf-8") as archivo:
    JUEGOS = json.load(archivo)

cliente = genai.Client(api_key=API_KEY) if API_KEY else None

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


def generar_respuesta(mensaje, historial):
    if cliente is None:
        raise RuntimeError(
            "Falta configurar GEMINI_API_KEY. Copiá .env.example a .env "
            "y pegá tu clave de https://aistudio.google.com/apikey."
        )

    contexto = construir_contexto(buscar_juegos(mensaje))
    sistema = f"{INSTRUCCIONES}\n\nContexto de la wiki:\n\n{contexto}"

    contenidos = []
    for turno in historial[-10:]:
        texto = str(turno.get("content", "")).strip()
        if not texto:
            continue
        rol = "user" if turno.get("role") == "user" else "model"
        contenidos.append(types.Content(role=rol, parts=[types.Part(text=texto)]))

    contenidos.append(types.Content(role="user", parts=[types.Part(text=mensaje)]))

    respuesta = cliente.models.generate_content(
        model=MODELO,
        contents=contenidos,
        config=types.GenerateContentConfig(
            system_instruction=sistema,
            temperature=0.4,
        ),
    )
    return respuesta.text


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
        return jsonify({"error": f"Error al consultar la IA: {error}"}), 502

    return jsonify({"respuesta": respuesta})


if __name__ == "__main__":
    app.run(debug=True)
