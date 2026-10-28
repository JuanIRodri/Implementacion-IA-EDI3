from math import sqrt


documentos = {
	"Texto A": ("Receta de pizza casera", [9, 1]),
	"Texto B": ("Cómo adiestrar a un perro", [1, 9]),
	"Texto C": ("Comida para gatos", [8, 8]),
}

consulta = "Galletas para perros"
vector_consulta = [7, 8]


def distancia_euclidiana(vector_a, vector_b):
	return sqrt(sum((a - b) ** 2 for a, b in zip(vector_a, vector_b)))


resultados = []
for identificador, (texto, vector) in documentos.items():
	distancia = distancia_euclidiana(vector_consulta, vector)
	resultados.append((distancia, identificador, texto))

resultados.sort()

print(f'Consulta: "{consulta}" -> {vector_consulta}')
for distancia, identificador, texto in resultados:
	vector = documentos[identificador][1]
	diferencia_x = vector[0] - vector_consulta[0]
	diferencia_y = vector[1] - vector_consulta[1]
	suma_cuadrados = diferencia_x ** 2 + diferencia_y ** 2
	print(
		f"{identificador}: {texto} | "
		f"d = sqrt(({diferencia_x})^2 + ({diferencia_y})^2) = "
		f"sqrt({suma_cuadrados}) = {distancia:.2f}"
	)

distancia, identificador, texto = resultados[0]
print(f"\nResultado más cercano: {texto} ({identificador})")
