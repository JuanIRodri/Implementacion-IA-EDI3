# GameWiki IA

Wiki de videojuegos con un chat IA que responde únicamente con información de los artículos.

## Objetivo

Implementar una IA con RAG (Retrieval Augmented Generation) que responda preguntas
únicamente con la información de una wiki de videojuegos.

## ¿Qué es RAG?

RAG significa "Recuperación + Generación". En lugar de que el modelo responda solo
con su conocimiento general, primero buscamos información relevante (los artículos)
y se la pasamos como contexto. Así responde con base en nuestros datos.

## Tecnologías usadas

- **Python 3** - Lenguaje base
- **Flask** - Servidor web
- **Google Gemini API** - Modelo de IA (gratis con API key)
- **google-genai** - SDK para conectarse a Gemini
- **python-dotenv** - Para guardar la API key de forma segura

## Cómo correrlo

### 1. Preparar el entorno
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar clave de Gemini
- Ir a [Google AI Studio](https://aistudio.google.com/apikey) y generar una API key
- Copiar `.env.example` a `.env` y pegar la clave:
```bash
cp .env.example .env
# editar .env con tu GEMINI_API_KEY
```

### 3. Ejecutar
```bash
python app.py
```

Abrir [http://localhost:5000](http://localhost:5000).

## Cómo funciona

- Los juegos están en `data/juegos.json`.
- `app.py` busca los artículos más relevantes al mensaje (búsqueda por palabras clave) y los pasa como contexto al modelo.
- El asistente está obligado a responder solo con esa información. Si no figura en la wiki, lo dice.
- Usa [google-genai](https://pypi.org/project/google-genai/) con Gemini 2.5 Flash.

## Implementación

### 1. Preparar el entorno
Ver la sección [Cómo correrlo](#cómo-correrlo).

### 2. Crear la base de datos (wiki)
Crear `data/juegos.json` con la información de cada juego:
- id, titulo, genero, año, desarrollador, plataformas, descripcion, datos_curiosos

### 3. Buscar información relevante
En `app.py` tenemos `buscar_juegos()`:
- Normalizamos el texto (quitamos tildes)
- Extraemos palabras clave
- Contamos coincidencias con cada artículo
- Retornamos los 4 más relevantes

Este paso es el "retrieval" (recuperación).

### 4. Pasar el contexto al modelo
Con `construir_contexto()` armamos un texto con los datos de los juegos
encontrados. Luego en `generar_respuesta()` le decimos al modelo:

```
Sos GameWiki IA, un asistente experto en videojuegos.
Respondés siempre en español.
Tenés que basarte ÚNICAMENTE en la información del contexto que se te proporciona.
Si la respuesta no está en el contexto, decilo honestamente.
No inventes datos ni fechas.
```

Este paso es el "augmentation" (aumentación).

### 5. Llamar a la IA (generación)
Usamos `google.genai.Client` con `generate_content()`. Pasamos:
- `model` - el modelo (gemini-2.5-flash)
- `contents` - historial + pregunta actual
- `system_instruction` - nuestras reglas + contexto

El modelo genera la respuesta basándose en el contexto.

### 6. Crear la interfaz web
- `templates/index.html` - Estructura HTML con la lista de juegos y el chat
- `static/style.css` - Estilos
- `static/app.js` - Envía preguntas al servidor con fetch(), muestra mensajes

## Puntos clave para entender

1. **No es fine-tuning** - No reentrenamos el modelo. Solo le pasamos contexto.
2. **Búsqueda simple** - Por palabras clave. Funciona bien para pocos artículos.
3. **Restricción al contexto** - Le pedimos explícitamente que no use conocimiento general.
4. **Historial** - Guardamos los últimos mensajes para mantener la conversación.

## Estructura

- `app.py` - Flask + lógica RAG simple
- `templates/index.html` - Página principal
- `static/style.css` - Estilos
- `static/app.js` - Lógica del chat
- `data/juegos.json` - Base de datos de la wiki

## Mejoras posibles

- Usar embeddings (sentence-transformers) para búsqueda semántica
- Añadir más juegos al JSON
- Guardar historial en base de datos
- Agregar streaming de respuestas

## Recursos

- [Google AI Studio](https://aistudio.google.com/) - Para obtener API key
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/)
- [Flask Docs](https://flask.palletsprojects.com/)
