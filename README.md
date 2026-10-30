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
- **Groq** - Proveedor de IA (OpenAI SDK, modelo `openai/gpt-oss-20b`)
- **OpenAI SDK** - Cliente para conectarse a Groq
- **python-dotenv** - Para guardar la API key de forma segura

## Cómo correrlo

### 1. Preparar el entorno
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar clave de Groq
- Ir a [Groq](https://console.groq.com/) y generar una API key
- Copiar `.env.example` a `.env` y pegar la clave:
```bash
cp .env.example .env
# editar .env con tu GROQ_API_KEY y GROQ_MODEL
```

### 3. Ejecutar
```bash
python app.py
```

Abrir [http://localhost:5000](http://localhost:5000).

## Cómo funciona

- Los juegos están en `data/juegos.json` (14 juegos).
- El asistente usa **function calling** con la tool `buscar_juegos` para buscar los artículos más relevantes al mensaje.
- Se arma contexto con los datos encontrados.
- El modelo genera una respuesta basándose en ese contexto.

## Implementación

### 1. Preparar el entorno
Ver la sección [Cómo correrlo](#cómo-correrlo).

### 2. Crear la base de datos (wiki)
Crear `data/juegos.json` con la información de cada juego:
- id, titulo, genero, año, desarrollador, plataformas, descripcion, datos_curiosos

### 3. Function calling (tool)
- Tool `buscar_juegos` con parámetros `{consulta: string}`.
- El loop llama al modelo → si hay tool calls → ejecuta → tool response → vuelve a llamar → hasta respuesta final.

### 4. Pasar el contexto al modelo
Con `construir_contexto()` armamos un texto con los datos de los juegos
encontrados. Luego en `generar_respuesta()` le decimos al modelo:

```
Sos GameWiki IA, un asistente experto en videojuegos.
Respondé siempre en español.
Tenés que basarte ÚNICAMENTE en la información del contexto que se te proporciona.
Si la respuesta no está en el contexto, decilo honestamente.
No inventes datos ni fechas.
```

### 5. Llamar a la IA (generación)
Usamos OpenAI SDK con Groq:
- `model` - el modelo (openai/gpt-oss-20b)
- `messages` - historial + pregunta actual
- `tools` - function calling
- `temperature` - 0.4

### 6. Crear la interfaz web
- `templates/index.html` - Estructura HTML con la lista de juegos y el chat
- `static/style.css` - Estilos
- `static/js/chat.js` - Lógica del chat (envía preguntas, muestra mensajes, tokens)
- `static/js/juegos.js` - Lógica de juegos (carga, render, paginación)

## Endpoints

- `GET /` → web con lista de juegos + chat.
- `POST /api/chat` → body `{ "mensaje": "...", "historial": [...] }`. Devuelve `{ "respuesta": "...", "usage": {...} }`.
- `GET /api/juegos?page=&por_pagina=` → lista paginada de juegos.

## Puntos clave para entender

1. **No es fine-tuning** - No reentrenamos el modelo. Solo le pasamos contexto / tools.
2. **Function calling** - El modelo decide cuándo buscar (tool).
3. **Contexto** - Se arma con los juegos relevantes encontrados.
4. **Historial** - Guardamos los últimos mensajes para mantener la conversación.

## Estructura

- `app.py` - Flask + lógica RAG con Groq + function calling
- `data/juegos.json` - Base de datos de la wiki (14 juegos)
- `templates/index.html` - Página principal
- `static/style.css` - Estilos
- `static/js/chat.js` - Lógica del chat
- `static/js/juegos.js` - Lógica de juegos
- `.env` - GROQ_API_KEY, GROQ_MODEL

## Mejoras posibles

- Usar embeddings (sentence-transformers) para búsqueda semántica
- Añadir más juegos al JSON
- Guardar historial en base de datos
- Agregar streaming de respuestas

## Recursos

- [Groq](https://console.groq.com/) - Para obtener API key
- [OpenAI SDK](https://platform.openai.com/)
- [Flask Docs](https://flask.palletsprojects.com/)
