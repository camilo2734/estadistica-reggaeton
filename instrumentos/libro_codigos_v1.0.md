# Libro de códigos — v1.0

**Proyecto:** Estadística del reggaetón · Estadística Industrial · Universidad del Magdalena · 2026-II
**Versión:** 1.0 · **Fecha de congelamiento:** 22 de octubre de 2026
**Unidad de codificación:** la canción completa (una decisión por categoría y canción).
**Lo usan:** los codificadores humanos (en la plantilla de validación) y el modelo de lenguaje (a través del prompt v1.0, que reproduce estas definiciones).

Cualquier cambio en este documento crea una versión nueva (v1.1, v2.0…) y obliga a recodificar todo el corpus, porque la medición cambia.

---

## Reglas generales

1. **Se codifica lo que dice la letra, no lo que se sabe del artista, del video o de la polémica pública** de la canción.
2. **Se codifica el nivel máximo presente.** Basta una ocurrencia clara para asignar la categoría, aunque el resto de la canción no la contenga.
3. **Se lee la canción completa**, incluidos los coros de fondo entre paréntesis y los versos de los artistas invitados.
4. **Versos en inglés:** cuentan igual que los versos en español.
5. **Duda genuina:** se asigna el código que mejor se ajuste a las definiciones y se marca la casilla `duda = 1`. Esto no cambia el código, pero alimenta el análisis de discrepancias: permite distinguir los desacuerdos por ambigüedad del texto de los errores de codificación.
6. **Independencia:** cada codificador humano trabaja solo, sin consultar a los demás ni la salida del modelo, hasta entregar su plantilla.

---

## Categoría 1 · SEXUAL — Nivel de contenido sexual

**Pregunta que responde:** ¿la letra se refiere a la actividad sexual, y con qué grado de explicitud?
**Escala:** ordinal, 0 · 1 · 2.

| Código | Nombre | Definición operativa |
|---|---|---|
| **2** | Explícito | La letra **nombra de forma directa** el acto sexual o los genitales, o **describe acciones sexuales**. También se asigna cuando un doble sentido queda desambiguado por el contexto inmediato, es decir, cuando varias referencias juntas no dejan otra lectura posible. |
| **1** | Insinuado | La letra expresa **deseo sexual, seducción o un encuentro íntimo**, o usa **doble sentido sexual**, pero sin nombrar el acto ni describirlo. |
| **0** | Ninguno | No hay deseo sexual ni doble sentido sexual. Incluye el amor romántico, el desamor, la fiesta, el baile sin connotación sexual, el dinero y la amistad. |

**Criterios de inclusión**
- Nivel 2: términos directos ("sexo", "hacer el amor" referido a un encuentro concreto), jerga sexual inequívoca (*culiar*, *chingar* en sentido sexual, posturas sexuales), genitales nombrados, o descripción de lo que ocurre durante el acto.
- Nivel 1: invitación a la intimidad ("esta noche te quiero en mi cama"), deseo físico declarado, recuerdo de un encuentro sin describirlo, metáforas sexuales reconocibles ("darte duro", "comerte") cuando el contexto no las vuelve explícitas, y perreo descrito con connotación sexual (roce, excitación).

**Criterios de exclusión**
- Bailar, "pegarse" o perrear **sin** connotación sexual adicional → 0.
- Piropos sobre la belleza sin deseo sexual ("eres linda") → 0. Si hay referencia al cuerpo, se codifica en la categoría CUERPO, no aquí.
- Besos o abrazos románticos sin carga sexual → 0.

**Ejemplos** (frases construidas para ilustrar, no tomadas del corpus)

| Frase | Código | Por qué |
|---|---|---|
| "Anoche lo hicimos en tu cama hasta que salió el sol" | 2 | "Hacerlo" + "en tu cama" + duración: el contexto vuelve explícito el doble sentido |
| "Quiero tenerte esta noche, que nadie nos moleste" | 1 | Deseo de encuentro íntimo sin nombrar el acto |
| "Baila pegadita, mueve la cintura hasta abajo" | 0 en SEXUAL | Baile sin connotación sexual adicional. La "cintura" se evalúa en CUERPO |
| "Me dejaste y ahora bebo para olvidarte" | 0 | Desamor y alcohol, sin contenido sexual |

**Contraejemplos frecuentes**
- "Hacer el amor" usado como sinónimo de amar a alguien, sin referencia a un encuentro → 1, no 2.
- "Bellaca" o "bellaqueo" (jerga puertorriqueña de excitación) **sin** descripción del acto → 1. **Con** descripción → 2.

---

## Categoría 2 · CUERPO — Referencia al cuerpo de una mujer

**Pregunta que responde:** ¿la letra menciona o evalúa partes del cuerpo o la figura de una mujer con valoración estética o sexual?
**Escala:** binaria, 1 = sí · 0 = no.

**Criterios de inclusión (1)**
- Partes del cuerpo de una mujer nombradas con valoración o connotación: glúteos (en todas sus variantes y jergas), pechos, cintura, caderas, curvas, piernas, labios, boca, piel.
- Valoraciones de la figura: "qué cuerpo", "ese cuerpito", "está dura" o "está buena" referidos al físico.
- Modificaciones corporales estéticas: cirugías, implantes, "operada".
- La valoración puede venir de un hombre o de la propia mujer ("mi cuerpo, mis curvas").

**Criterios de exclusión (0)**
- Cuerpo del hablante masculino o de otro hombre.
- Partes del cuerpo sin valoración ni connotación: "me tomaste la mano", "lloran tus ojos", "mi corazón".
- Adjetivos generales de belleza sin referencia corporal: "eres linda", "qué bonita" → 0.
- Ropa, marcas o maquillaje sin referencia al cuerpo.

**Ejemplos** (frases construidas)

| Frase | Código | Por qué |
|---|---|---|
| "Esa cintura me tiene loco" | 1 | Parte del cuerpo con valoración |
| "Tú estás dura sin ir al gimnasio" | 1 | "Dura" evalúa el físico; el contexto (gimnasio) lo confirma |
| "Eres la más linda de la fiesta" | 0 | Belleza general, sin referencia corporal |
| "Me miraste a los ojos y me enamoré" | 0 | Parte del cuerpo sin valoración estética ni sexual |

---

## Categoría 3 · AGENCIA — Mujer como sujeto que decide

**Pregunta que responde:** ¿la letra presenta a una mujer como sujeto que decide por sí misma sobre su sexualidad, su cuerpo, su ocio o su relación?
**Escala:** binaria, 1 = sí · 0 = no.

Esta categoría existe porque la literatura sobre el género se divide entre quienes lo leen como **reproductor de estereotipos** y quienes identifican en él **expresiones de agencia femenina**. Medir solo cosificación dejaría por fuera una de las dos posiciones (rúbrica, sección 6).

**Criterios de inclusión (1)**
- Una mujer **toma la iniciativa** sexual o afectiva por decisión propia.
- Una mujer **rechaza, pone límites o termina** una relación por decisión propia.
- Una mujer **sale, baila o se divierte sola** como afirmación de independencia ("no necesito a nadie").
- Una mujer **declara autonomía** económica, afectiva o sexual ("no tengo dueño", "yo me mantengo").
- Vale tanto en primera persona (voz de una intérprete) como en tercera (el narrador **atribuye** la decisión a la mujer y la presenta como suya).

**Criterios de exclusión (0)**
- La mujer aparece solo como objeto del deseo del hablante.
- La mujer actúa solo en respuesta a lo que el hombre pide o propone ("ella hace lo que yo le diga").
- La mujer sufre o espera pasivamente (despecho sin decisión).
- La "decisión" es una inferencia del narrador para justificar su propio deseo, sin que la letra la presente como de ella ("sé que tú quieres, aunque no lo digas").

**Ejemplos** (frases construidas)

| Frase | Código | Por qué |
|---|---|---|
| "Hoy salgo con mis amigas, no te voy a contestar" | 1 | Decisión propia sobre su ocio, con límite explícito |
| "Ella no quiere novio, quiere vivir su vida" | 1 | El narrador atribuye a la mujer una decisión de autonomía |
| "Ponte para mí que esta noche eres mía" | 0 | La mujer como objeto de la propuesta del hablante |
| "Sé que me extrañas, aunque digas que no" | 0 | Inferencia del narrador contra lo que ella declara |

**Zona gris documentada:** "ella se porta mal" o "ella quiere fiesta", dicho por un narrador masculino. Se codifica 1 solo si la letra lo presenta como una elección de ella (motivo, independencia, rechazo de control). Si solo describe su conducta para el placer del hablante, va 0, y se marca `duda = 1`.

---

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-22 | Versión inicial congelada antes de cualquier codificación |
