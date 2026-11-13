# Pendiente: Búsqueda semántica + Streaming

## Estado actual (ya implementado)
- Alias/abreviaturas de juegos (hk, gta, lol, wow, mc, etc.) en `app.py` (`ALIAS`)
- Campos extra en `data/juegos.json`: clasificacion, precio, jugadores, motor, duracion, puntuacion, tags, enlace
- Uso de tokens en una línea al fondo del chat (`static/js/chat.js`)

## Qué falta instalar
```bash
.venv/bin/pip install sentence-transformers numpy
```

## Qué falta implementar
1. **Búsqueda semántica (embeddings)**
   - Generar embeddings de los artículos de `data/juegos.json`
   - Usar `sentence-transformers` (modelo ligero: `all-MiniLM-L6-v2`, ~80-100 MB RAM)
   - Reemplazar/ complementar la búsqueda por coincidencia de palabras con búsqueda por similitud coseno
   - Guardar embeddings en caché para no regenerar en cada inicio

2. **Streaming de respuestas (Server-Sent Events)**
   - Endpoint `/api/chat/stream` que envíe tokens progresivamente al frontend
   - Actualizar `static/js/chat.js` para mostrar el texto a medida que llega

## Cómo correr el proyecto
```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # editar con GROQ_API_KEY
python app.py
# Abrir http://127.0.0.1:5000
```

## Archivos clave
- `app.py` - Flask + lógica RAG con Groq + function calling
- `data/juegos.json` - Base de datos de la wiki
- `templates/index.html` - Página principal
- `static/js/chat.js` - Lógica del chat
- `static/style.css` - Estilos
- `.env` - GROQ_API_KEY, GROQ_MODEL