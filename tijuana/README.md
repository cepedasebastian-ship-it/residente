# TIJUANA — v1

Motor de diálogo con **dos compuertas**, sacado del prototipo `cantinero.py` y
convertido en proyecto: contenido en JSON, reglas en Python, tests que
garantizan que el caso se puede resolver.

Despertaste en una bañera con hielo, te falta un riñón y no te acordás de nada.
El cantinero del Bar Sirena sabe qué pasó. Hay dos problemas:

1. **¿Te entendió?** Habla inglés roto. Frases largas en inglés no le llegan.
2. **¿Te dice la verdad?** Miente por miedo. Cada verdad tiene su llave.

```
cd tijuana
python -m tijuana            # jugar (no necesita ni instalar ni API key)
python -m tijuana --demo     # ver el recorrido completo en 5 turnos
pytest                       # 69 tests, < 1 s
```

---

## Cómo se juega

Todo lo que escribas es hablarle, en español o en inglés. Los comandos empiezan
con `/`:

| Comando | Qué hace |
| --- | --- |
| `/mostrar aro \| pulsera \| cicatriz` | Le mostrás algo. Se usa en tu **próxima** frase. |
| `/pruebas` | Qué llevás encima. |
| `/dic` | Abrís el diccionario: te hacés entender mejor ese turno. |
| `/estado` | Confianza, presión y tablero Memento. |
| `/pistas` | Qué le falta a cada verdad (spoilers). |
| `/debug` | Muestra u oculta el panel de compuertas. |
| `/salir` | Te vas del bar. |

### Las dos compuertas

**Compuerta 1 — comprensión.** Si le hablás en español, te entiende siempre. En
inglés arranca en 0.35 y se mueve: mostrarle algo suma 0.25, el diccionario
0.20, una frase de hasta 4 palabras suma 0.10 y una de más de 12 resta 0.25.
Con 0.65 te entiende, con 0.40 te entiende a medias, con menos se pierde. Si no
te entendió, **no revela nada** por más llaves que tengas.

**Compuerta 2 — verdad.** Cada verdad exige un concepto (de qué le estás
hablando, sin importar las palabras exactas) más una llave: una prueba,
confianza acumulada, presión, o haber destrabado otra verdad antes.

```
la_chica                 + (aro | presión≥2 | confianza≥2)   -> Marisol estaba ASUSTADA
quienes_te_hicieron_esto + (pulsera y confianza≥1)           -> Gente de la red pasa por el bar
a_donde_te_llevaron      + esa verdad + (presión≥1 | conf≥2) -> Hay una puerta en el fondo
que_dijo_marisol         + la primera verdad + confianza≥3   -> Marisol te ADVIRTIÓ
```

### Los diales

**Confianza** (0-5): cada fuente suma **una sola vez** — mostrar la pulsera,
mostrar la cicatriz, hablar de lo que te hicieron, ser amable y hablarle en su
idioma. El aro no da confianza: es una llave.

**Presión** (0-5): sube si apretás o si insistís sobre algo que ya te negó, y
**baja** si aflojás. A partir de 3 se cierra y no suelta nada.

---

## Estructura

```
tijuana/
├── src/tijuana/
│   ├── modelos.py       qué es una verdad, una mentira, una condición
│   ├── carga.py         lee y VALIDA los JSON
│   ├── idioma.py        idioma, conceptos y tono
│   ├── compuertas.py    compuerta 1 y compuerta 2
│   ├── diales.py        confianza y presión
│   ├── estado.py        partida en curso + tablero Memento
│   ├── motor.py         un turno de punta a punta
│   ├── cli.py           el REPL (solo entrada/salida)
│   ├── narradores/      plantillas (por defecto) y llm (opcional)
│   └── datos/           EL CONTENIDO: caso.json, npcs/, lexico.json, guiones/
└── tests/
```

La división que importa: **el motor decide qué puede decir el NPC, el narrador
decide cómo lo dice.** Por eso se puede cambiar la plantilla por un LLM sin
tocar una línea de reglas, y por eso el LLM no puede inventar trama: recibe la
lista cerrada de lo que está autorizado a revelar este turno.

El motor no imprime nada — devuelve un objeto `Turno`. La CLI es una de las
formas de mostrarlo; una web o un bot serían otras.

```python
from tijuana import Motor, cargar_contenido

motor = Motor(cargar_contenido())
motor.mostrar("aro")
turno = motor.turno("¿te acuerdas de esta chica?")

turno.respuesta        # "...Sí. Estaba aquí. Y estaba asustada..."
turno.ids_revelados    # ['marisol_estaba_asustada']
motor.completo()       # False
```

---

## Escribir contenido

Todo el contenido está en `src/tijuana/datos/`. No hace falta tocar Python para
agregar un NPC o mover una llave.

- **`caso.json`** — pruebas que lleva el jugador y tablero Memento inicial.
  Las tarjetas de tipo `creencia` son las cosas falsas que el jugador da por
  ciertas; las verdades las tachan.
- **`npcs/<id>.json`** — conceptos (sinónimos ES/EN), verdades con sus
  requisitos, mentiras con su *tell*, y las reacciones fijas.
- **`lexico.json`** — marcadores de idioma y de tono, compartidos por todos.
- **`guiones/*.txt`** — partidas grabadas, una entrada por línea.

Para agregar un NPC: creá `npcs/mesera.json`, agregalo a `npcs` en `caso.json`
y jugá con `python -m tijuana --npc mesera`. El cargador valida al arrancar que
cada mentira tape una verdad existente, que cada verdad apunte a un concepto
que existe, que no haya ciclos de dependencias y que lo que se contradice sea
una creencia real del tablero. Un JSON mal escrito falla al cargar, con el
nombre del campo, y no en medio de una partida.

### Requisitos de una verdad

```json
"requiere": {
  "concepto": "la_chica",          // obligatorio: de qué hay que hablar
  "confianza_min": 2,              // se cumple todo esto (AND)...
  "presion_min": 0,
  "verdades_previas": ["otra_id"],
  "cualquiera_de": [               // ...y al menos una de estas (OR)
    { "prueba": "aro" },
    { "presion_min": 2 }
  ]
}
```

---

## Modo LLM (opcional)

```sh
pip install -e '.[llm]'
export ANTHROPIC_API_KEY=...      # o: ant auth login
python -m tijuana --llm
```

Usa `claude-opus-5` (cambiable con `--modelo` o `TIJUANA_MODELO`). El prompt
del sistema se arma **desde el estado del turno**: solo las verdades que el
motor autorizó, las mentiras que el NPC sigue sosteniendo, si entendió y cómo
están los diales. Si falta el paquete, no hay credenciales, se cae la red o el
modelo declina responder, se usa el narrador de plantillas y la partida sigue.

---

## Qué cambió respecto del prototipo

Además de la separación en módulos y el contenido en JSON, se corrigieron
cuatro cosas que el prototipo hacía mal:

1. **El tablero se llenaba aunque el cantinero se cerrara.** Con presión alta
   respondía "bájale, amigo" y el jugador igual se llevaba la verdad anotada.
   Ahora, si se cierra, no hay revelación.
2. **Los conceptos se buscaban por subcadena.** `"her"` matcheaba dentro de
   `"there"` y `"back"` dentro de `"background"`. Ahora la búsqueda es por
   palabra completa.
3. **La confianza se podía farmear.** Repetir "cicatriz" cinco veces daba
   confianza 5. Ahora cada fuente suma una sola vez.
4. **La presión no bajaba nunca.** Tres frases bruscas dejaban la partida
   trabada para siempre. Ahora aflojar la baja.

También: hablarle en su idioma ahora suma confianza (era un `+0` con un
comentario "podés premiar esto si querés"), la comprensión parcial tiene su
propia reacción, y el LLM recibe el historial de la charla para no repetirse.

---

## Tests

```sh
pytest -q
```

El que más importa es `test_el_guion_de_demo_destraba_las_cuatro_verdades`:
reproduce `datos/guiones/demo.txt` y verifica que el caso siga siendo
resoluble. Si alguien mueve una llave y rompe el recorrido, ese test avisa.
