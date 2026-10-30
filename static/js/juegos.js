let paginaJuegos = 1;
let totalPaginasJuegos = 1;
let juegosActuales = [];

function crearTarjetaJuego(juego) {
  const articulo = document.createElement("article");
  articulo.className = "juego";
  articulo.innerHTML =
    '<div class="juego-cabecera"><h3>' + juego.titulo + '</h3><span class="anio">' + juego.anio + '</span></div>' +
    '<p class="genero">' + juego.genero + ' · ' + juego.desarrollador + '</p>' +
    '<p class="descripcion">' + juego.descripcion + '</p>' +
    '<p class="plataformas">' + juego.plataformas.join(' · ') + '</p>' +
    '<div class="curiosidad"><strong>Dato curioso:</strong> ' + juego.datos_curiosos + '</div>';
  return articulo;
}

function crearPaginacion(pagina, totalPaginas, onCambiarPagina) {
  const contenedor = document.getElementById("juegos");
  const paginacion = document.createElement("div");
  paginacion.id = "paginacion-juegos";
  paginacion.className = "paginacion-juegos";

  const anterior = document.createElement("button");
  anterior.id = "pag-anterior";
  anterior.type = "button";
  anterior.textContent = "← Anterior";
  anterior.disabled = pagina <= 1;
  anterior.addEventListener("click", () => onCambiarPagina(pagina - 1));

  const siguiente = document.createElement("button");
  siguiente.id = "pag-siguiente";
  siguiente.type = "button";
  siguiente.textContent = "Siguiente →";
  siguiente.disabled = pagina >= totalPaginas;
  siguiente.addEventListener("click", () => onCambiarPagina(pagina + 1));

  const info = document.createElement("span");
  info.className = "pagina-info";
  info.textContent = "Página " + pagina + " de " + totalPaginas;

  paginacion.appendChild(anterior);
  paginacion.appendChild(info);
  paginacion.appendChild(siguiente);
  return paginacion;
}

function renderizarJuegos() {
  const contenedor = document.getElementById("juegos");
  contenedor.innerHTML = "";
  for (const juego of juegosActuales) {
    contenedor.appendChild(crearTarjetaJuego(juego));
  }
  const anterior = document.getElementById("paginacion-juegos");
  if (anterior) {
    anterior.remove();
  }
  contenedor.parentElement.appendChild(
    crearPaginacion(paginaJuegos, totalPaginasJuegos, (pagina) => cargarJuegos(pagina))
  );
}

async function cargarJuegos(pagina = 1) {
  const respuesta = await fetch("/api/juegos?page=" + pagina + "&por_pagina=6");
  const datos = await respuesta.json();
  juegosActuales = datos.juegos;
  totalPaginasJuegos = datos.total_paginas;
  paginaJuegos = datos.pagina;
  renderizarJuegos();
}

async function initJuegos() {
  await cargarJuegos();
}

export { initJuegos };
