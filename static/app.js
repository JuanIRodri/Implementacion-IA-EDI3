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
      throw new Error(datos.error || "No se pudo obtener una respuesta.");
    }

    pendiente.remove();
    agregarMensaje("bot", datos.respuesta);

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
