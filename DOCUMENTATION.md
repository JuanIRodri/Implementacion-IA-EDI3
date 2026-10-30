# GameWiki IA — Documentación

## Qué es
Wiki de videojuegos con un chat IA (RAG) que responde preguntas usando la información de los artículos en `data/juegos.json`.

## Estado actual
- El chat está funcionando con Groq (OpenAI SDK, `base_url="https://api.groq.com/openai/v1"`, modelo `openai/gpt-oss-20b`).
- Function calling implementado: la tool `buscar_juegos` busca en la wiki y devuelve resultados.
- Frontend modularizado: `static/js/chat.js` (chat) y `static/js/juegos.js` (juegos + paginación).
- Paginación en `/api/juegos` (`?page=&por_pagina=`, devuelve `juegos`, `total`, `total_paginas`).
- Uso de tokens expuesto en `/api/chat` (`respuesta` + `usage`).

## Cómo correr
```bash
source .venv/bin/activate
python app.py
```
Abrir http://localhost:5000

## Endpoints
- `GET /` → web con lista de juegos + chat.
- `POST /api/chat` → body `{ "mensaje": "...", "historial": [...] }`. Devuelve `{ "respuesta": "...", "usage": {...} }`.
- `GET /api/juegos?page=&por_pagina=` → lista paginada de juegos.

## Implementación de la IA (Groq + Function Calling)

### 1. Cliente
```python
cliente = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=API_KEY)
```

### 2. Agente con function calling (`generar_respuesta`)
```python
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
```

### 3. Tool (function calling)
```python
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
```

### 4. Flujo RAG
1. `buscar_juegos` → tool → `ejecutar_tool`.
2. Se arma `mensajes` con system + historial + user + tool response.
3. Se llama a Groq de nuevo → respuesta final.

## Estructura relevante
- `app.py` → Flask + RAG + Groq (OpenAI SDK).
- `data/juegos.json` → wiki (14 juegos).
- `templates/index.html` → UI (chat + juegos).
- `static/js/chat.js`, `static/js/juegos.js` → frontend modular.
- `static/style.css` → estilos.

## Errores vistos / fixes
- Modelo Gemini inexistente → cambié a Groq.
- Paginación no movía → bug `?page` vs `?pagina`.
- `'ChatCompletionMessage' object has no attribute 'get'` → usar atributos OpenAI.
- Error 503 → alta demanda temporal de Groq/Google.

## Tools / tecnologías
- Python 3, Flask, OpenAI SDK (Groq), python-dotenv.
- Groq para el modelo de IA (free tier).
