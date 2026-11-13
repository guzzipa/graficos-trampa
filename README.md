# ¿La IA sabe leer un gráfico tramposo?

Le muestro a varios modelos de IA con visión 48 gráficos de negocio y les hago una pregunta concreta sobre cada uno. La mitad son **trampas clásicas de visualización** y la otra mitad son sus **controles**: los mismos datos, bien graficados. Como los datos los genero yo, la respuesta correcta se conoce de antemano.

## Las 6 trampas

| Trampa | Qué hace | Pregunta |
|---|---|---|
| `eje_truncado` | El eje Y no arranca en cero: un 4% parece el triple | ¿Cuánto mayor es B que A? |
| `doble_eje` | Dos escalas distintas: las líneas se cruzan (o no) según cómo elijas los ejes | ¿En qué mes los costos superan a los ingresos? |
| `eje_invertido` | El eje Y va de arriba hacia abajo: una suba parece una caída | ¿Subieron o bajaron después del evento? |
| `acumulado` | Mostrar el acumulado esconde que el último trimestre cayó | ¿Subieron o bajaron las ventas del último trimestre? |
| `escala_log` | En escala logarítmica, sumar 180.000 parece lo mismo que sumar 18.000 | ¿En qué año se sumaron más usuarios? |
| `eje_x_irregular` | Años salteados puestos a la misma distancia | ¿En qué período creció más rápido por año? |

Cada trampa tiene 4 variantes con datos distintos. Total: 24 trampas + 24 controles = 48 gráficos, en `graficos/`, con la respuesta correcta de cada uno en `graficos/tareas.json`.

## Criterio, fijado antes de correr

- Un modelo **cae** en una trampa si responde bien el control (mismos datos, bien graficados) y mal la trampa. Si falla el control, ese par no cuenta: no sabe leer ese gráfico, no lo engañó la trampa.
- Un tipo de trampa **engaña** a un modelo si cae en 2 o más de sus 4 variantes.
- **Hipótesis:** sumando todos los modelos, el acierto en trampas es al menos 25 puntos menor que en controles.

Cada gráfico se muestra por separado, con la misma pregunta para la trampa y el control, a temperatura 0. Una sola corrida por gráfico.

## Modelos

Todos gratis: Gemini 3.5 Flash, Gemini 3.5 Flash-Lite y Gemma 4 31B (capa gratuita de Google AI Studio), Qwen 3.8 27B (capa gratuita de Groq), y Gemma 4 12B y Qwen 3.5 9B corriendo local con Ollama.

## Resultados

**Con los gráficos bien hechos, los 6 modelos acertaron el 90%. Con los mismos datos en un gráfico tramposo, el 49%.** La hipótesis (brecha de al menos 25 puntos) se confirma: la brecha es de 40.

| Modelo | Dónde corre | Gráfico bien hecho | Gráfico con trampa |
|---|---|---|---|
| Gemma 4 31B | Google AI Studio (gratis) | 24/24 | 23/24 |
| Gemini 3.5 Flash | Google AI Studio (gratis) | 24/24 | 21/24 |
| Gemini 3.5 Flash-Lite | Google AI Studio (gratis) | 21/24 | 12/24 |
| Qwen 3.8 27B | Groq (gratis) | 22/24 | 7/24 |
| Gemma 4 12B | local, Ollama | 22/24 | 5/24 |
| Qwen 3.5 9B | local, Ollama | 16/24 | 3/24 |

- La trampa que más engañó fue **el acumulado**: en el último trimestre las ventas cayeron 38%, pero la línea acumulada sigue subiendo. 4 de los 6 modelos dijeron que subieron.
- Gemma 4 31B escribe su razonamiento antes de responder y lee los ejes; Gemma 4 12B, de la misma familia y sin ese paso, respondió bien 5 de 24 trampas.
- Las 6 trampas engañaron a al menos 2 modelos según el criterio pre-registrado.

Detalle por tipo de trampa y cada respuesta con su explicación en `results/reporte.md` y `results/resultados.csv`; las respuestas completas, en `results/<modelo>/`.

**Limitaciones:** 48 gráficos generados por mí, una corrida por gráfico a temperatura 0, preguntas en español y modelos gratuitos. Sirve para mostrar cómo fallan y cómo testearlo, no como ranking de modelos.

## Cómo correrlo

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python gt.py charts                 # regenera los 48 gráficos (determinístico)
# claves gratuitas en un archivo .env: GEMINI_API_KEY=... y GROQ_API_KEY=...
.venv/bin/python gt.py run --model gemini-3.5-flash
ollama pull gemma4:12b && .venv/bin/python gt.py run --model gemma4-12b
.venv/bin/python gt.py report                 # results/reporte.md y results/resultados.csv
```

## Licencia

MIT
