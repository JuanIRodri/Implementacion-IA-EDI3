const form = document.getElementById("form-chat");
const entrada = document.getElementById("entrada");
const botonEnviar = document.getElementById("enviar");
const mensajes = document.getElementById("mensajes");
const reiniciar = document.getElementById("reiniciar");

let historial = [];
let cargando = false;

const saludo =
  "Hola. Soy GameWiki IA. Preguntame por los juegos de la wiki: género, " +
  "año, curiosidades o de qué trata cada uno.";

function agregarMensaje(tipo, texto, claseExtra) {
  const burbuja = document.createElement("div");
  burbuja.className = "mensaje " + tipo + (claseExtra ? " " + claseExtra : "");
  burbuja.textContent = texto;
  mensajes.appendChild(burbuja);
  mensajes.scrollTop = mensajes.scrollHeight;
  return burbuja;
}

async function enviarPregunta(texto) {
  agregarMensaje("usuario", texto);
  const pendiente = agregarMensaje("bot", "Pensando...", "cargando");

  cargando = true;
  botonEnviar.disabled = true;

  try {
    const respuesta = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje: texto, historial }),
    });

    const datos = await respuesta.json();

    if (!respuesta.ok) {
      let textoError = "No se pudo obtener una respuesta de la IA.";
      if (respuesta.status === 503) {
        textoError = "La IA está con alta demanda en este momento. Probá de nuevo en unos minutos.";
      } else if (respuesta.status === 429) {
        textoError = "Límite de uso de la IA alcanzado. Probá más tarde.";
      } else {
        textoError = datos.error || textoError;
      }
      throw new Error(textoError);
    }

    pendiente.remove();
    agregarMensaje("bot", datos.respuesta);

    const usoDiv = document.getElementById("uso-api");
    if (usoDiv) {
      usoDiv.textContent = "Tokens usados: " + (datos.usage && datos.usage.total_tokens ? datos.usage.total_tokens : "–") + " · prompt: " + (datos.usage && datos.usage.prompt_tokens ? datos.usage.prompt_tokens : "–") + " · respuesta: " + (datos.usage && datos.usage.completion_tokens ? datos.usage.completion_tokens : "–");
    }

    historial.push({ role: "user", content: texto });
    historial.push({ role: "assistant", content: datos.respuesta });
  } catch (error) {
    pendiente.remove();
    agregarMensaje("error", error.message);
  } finally {
    cargando = false;
    botonEnviar.disabled = false;
    entrada.focus();
  }
}

function initChat() {
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const texto = entrada.value.trim();
    if (!texto || cargando) return;
    entrada.value = "";
    enviarPregunta(texto);
  });

  reiniciar.addEventListener("click", () => {
    historial = [];
    mensajes.innerHTML = "";
    agregarMensaje("bot", saludo);
    entrada.focus();
  });
}

export { initChat };
