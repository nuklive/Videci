# Wikidata Reference — Publicación de eventos VIDECI

Referencia para Fase 6 (publicación masiva en Wikidata vía QuickStatements).

## Criterios de publicación (ESTRICTOS)

- Publicar SOLO crisis (año+departamento) con estado `verificado` o `corroborado`
- NUNCA publicar `corroborado_debil` ni `no_verificado`
- Cada statement nuevo DEBE llevar referencia (URL de fuente + fecha de consulta)
- Granularidad: **una crisis departamental = un item candidato**. NO crear items por registro municipal VIDECI (no son notables individualmente; los municipios van como qualifiers o en la descripción)
- Crisis cuya única fuente es EM-DAT: publicable, pero preferir crisis con fuente web adicional

## QIDs verificados (2026-07-06, contra API en vivo)

### Tipos de evento (P31)

| Tipo VIDECI | QID | Label |
|---|---|---|
| sequia | Q43059 | drought |
| inundacion | Q8068 | flood |
| incendio | Q169950 | wildfire |
| deslizamiento | Q167903 | landslide |
| granizada | Q61071643 | hailstorm |
| helada | Q642683 | cold wave (usar para heladas severas; para helada agrícola puntual, resolver en runtime con wbsearchentities y confirmar con el usuario) |

### Geografía

| Entidad | QID |
|---|---|
| Bolivia (P17) | Q750 |
| Departamento del Beni | Q233169 |
| Departamento de Cochabamba | Q233917 |
| Departamento de Tarija | Q233933 |
| Departamento de Santa Cruz | Q235106 |
| Departamento de Chuquisaca | Q235110 |
| Departamento de Pando | Q235362 |
| Departamento de Potosí | Q238079 |
| Departamento de La Paz | Q272784 |
| Departamento de Oruro | Q1061368 |

(Q844510 "Departamento del Litoral" es histórico — ignorar.)

### Propiedades

| Propiedad | PID | Uso |
|---|---|---|
| instance of | P31 | tipo de evento |
| country | P17 | Q750 |
| located in admin. entity | P131 | QID del departamento |
| point in time | P585 | año con precisión de año: `+2007-00-00T00:00:00Z/9` |
| start time / end time | P580/P582 | solo si la fuente da rango de meses |
| reference URL (en referencia) | S854 | URL de la fuente verificada |
| retrieved (en referencia) | S813 | fecha de consulta: `+2026-07-06T00:00:00Z/11` |
| title (en referencia) | S1476 | título de la fuente: `es:"..."` |

Para propiedades de impacto (muertes, afectados): NO hay propiedad estándar para "familias afectadas". Si la fuente da número de muertes usar P1120 (number of deaths). Otros conteos: resolver PID en runtime con `wbsearchentities` (type=property) y confirmar con el usuario antes de incluir en el batch — no adivinar PIDs.

## Reconciliación (OBLIGATORIA antes de crear)

Buscar items existentes para evitar duplicados. SPARQL (GET a `https://query.wikidata.org/sparql`, header `Accept: application/sparql-results+json`, User-Agent descriptivo):

```sparql
SELECT ?item ?itemLabel ?fecha ?depto ?deptoLabel WHERE {
  ?item wdt:P31/wdt:P279* wd:{QID_TIPO} ;
        wdt:P17 wd:Q750 .
  OPTIONAL { ?item wdt:P585 ?fecha . }
  OPTIONAL { ?item wdt:P580 ?fecha . }
  OPTIONAL { ?item wdt:P131 ?depto . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
}
```

Filtrar por año localmente. Complementar con `wbsearchentities` en es/en ("sequía Bolivia {year}", "{year} Bolivia drought").

Matching:
- Item existente mismo tipo+año+departamento → **actualizar** ese QID (añadir statements/referencias faltantes), no crear
- Item nacional del mismo año (sin P131 o multi-departamento) → añadir P131 del departamento + referencia al item existente; no crear item departamental paralelo salvo que el usuario lo pida
- Sin match → candidato a **crear**

## Sintaxis QuickStatements (V1, tab-separated)

Crear item nuevo:

```
CREATE
LAST	Les	"Sequía de 2007 en el departamento de La Paz"
LAST	Len	"2007 drought in La Paz Department, Bolivia"
LAST	Des	"sequía que afectó N municipios del departamento de La Paz, Bolivia"
LAST	Den	"drought affecting N municipalities of La Paz Department, Bolivia"
LAST	P31	Q43059	S854	"https://fuente..."	S813	+2026-07-06T00:00:00Z/11
LAST	P17	Q750
LAST	P131	Q272784	S854	"https://fuente..."	S813	+2026-07-06T00:00:00Z/11
LAST	P585	+2007-00-00T00:00:00Z/9	S854	"https://fuente..."	S813	+2026-07-06T00:00:00Z/11
```

Actualizar item existente: igual pero con el QID en lugar de `LAST` (sin línea CREATE):

```
Q12345678	P131	Q272784	S854	"https://fuente..."	S813	+2026-07-06T00:00:00Z/11
```

Reglas:
- Separador TAB real, no espacios
- Strings entre comillas dobles; labels/descriptions con prefijo de idioma (`Les`/`Den`...)
- Fechas: `+YYYY-MM-DDT00:00:00Z/precision` — /9 año, /11 día
- Cada statement sustantivo lleva su referencia (S854 + S813; S248 "stated in" si la fuente tiene item propio, ej. EM-DAT)
- Para fuentes EM-DAT: S854 `"https://public.emdat.be/"` + anotar DisNo en la descripción o S1476

## Ejecución (siempre por el usuario)

1. Guardar batch en `Research/videci-wikidata-{tipo}-{fecha}.qs`
2. Usuario abre https://quickstatements.toolforge.org → login con cuenta Wikimedia → New batch → pegar comandos V1
3. **Ejecutar primero en modo preview** y revisar cada comando
4. Correr como batch CON nombre descriptivo (ej. "VIDECI drought verification 2002-2023") — los batches quedan registrados en EditGroups y son reversibles en bloque: https://editgroups.toolforge.org
5. Batches grandes (>100 items nuevos): correr una muestra de 5-10 primero, revisar en Wikidata, luego el resto

## Eventos/campañas (CampaignEvents)

Si el usuario participa en un evento de edición (Special:EventDetails/{id}), las ediciones NO se asocian solas: la extensión muestra un diálogo post-edición solo en la interfaz web. Ediciones por API (bot password, scripts) quedan fuera del panel de contribuciones del evento.

- **Asociar cada edición inmediatamente después de crearla**, mientras el evento está activo:
  `PUT https://www.wikidata.org/w/rest.php/campaignevents/v0/event_registration/{eventId}/edits/wikidatawiki/{revid}` con body `{"token": csrf}` y la misma sesión autenticada
- El endpoint **rechaza asociaciones cuando el evento ya cerró** (`event-not-active`), aunque la revisión esté dentro del plazo — no hay asociación retroactiva; solo un organizador puede reabrir extendiendo la fecha de fin
- Preguntar al usuario ANTES de publicar si el batch debe contar para algún evento

## Política y etiqueta

- Notabilidad (WD:N): crisis departamentales con fuentes independientes serializables cumplen el criterio estructural; aun así, ante duda, preferir enriquecer items existentes sobre crear nuevos
- No re-correr el mismo batch si falla a medias — QuickStatements no es idempotente en CREATE (crearía duplicados). Identificar qué comandos corrieron y continuar desde ahí
- Máximo respeto a datos existentes: nunca sobrescribir statements con rank/valores existentes; solo añadir
- Rate: QuickStatements maneja el throttling por sí mismo; no correr múltiples batches en paralelo
