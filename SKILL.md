---
name: videci-verify
description: Verificador de datos VIDECI. Toma un CSV de eventos de desastre del sistema VIDECI de Bolivia y verifica contra fuentes independientes usando agentes paralelos, en tres modos - muestra estratificada, completo (todas las crisis año+departamento), o híbrido. Produce nota de investigación, HTML interactivo, CSV enriquecido, y opcionalmente un batch de QuickStatements para publicar las crisis verificadas en Wikidata. Usar cuando el usuario diga "verificar videci", "videci verify", "verificar datos videci", o "spot check videci".
argument-hint: "[ruta_archivo] [tamaño_muestra?] [modo?] — ruta al CSV de VIDECI, opcionalmente tamaño de muestra (default: 25), modo: 'muestra' (default), 'completo' o 'hibrido'"
---

# Verificador de Datos VIDECI

Skill híbrido: la orquestación corre en la conversación principal (el usuario ve y aprueba cada paso), los agentes hacen el trabajo pesado de búsqueda en paralelo.

Idioma principal: **español**. Los agentes buscan fuentes en español e inglés.

---

## Fase 1 — Lectura y Análisis del Dataset

1. **Leer el CSV de VIDECI** en la ruta proporcionada
   - Columnas esperadas: `Tipo de Evento`, `Fam. afec.`, año, departamento, provincia, municipio. Si los nombres difieren (el formato de exportación de VIDECI puede cambiar), mapear las columnas equivalentes antes de continuar y reportar el mapeo al usuario
2. **Auto-detectar el tipo de evento** desde la columna `Tipo de Evento`:
   - Contar ocurrencias de cada tipo
   - Mapear tipos compuestos al tipo primario usando `mapeo_compuestos` de `source-hierarchies.yml`
   - Identificar el tipo dominante y reportar la distribución
3. **Cargar EM-DAT como fuente de corroboración local** (si existe):
   - Leer `Research/emdat-bolivia-climatological.csv`
   - Filtrar por `Disaster Type` que corresponda al tipo VIDECI detectado (ej: "Drought" para sequía)
   - Extraer para cada registro EM-DAT: año, departamentos (del campo `Location` y `Admin Units`/`GADM Admin Units`), total afectados
   - Construir un índice `{año → [departamentos]}` para matching rápido en Fase 3
   - Reportar: "EM-DAT tiene N eventos de {tipo} en Bolivia en el rango {año_min}-{año_max}"
   - Si el archivo no existe, continuar sin EM-DAT (solo reduce corroboración automática)
   - **NOTA**: este CSV solo cubre eventos climatológicos (sequía y afines). Para tipos no climatológicos (inundación → hydrological, deslizamiento → geological, incendio → wildfire en EM-DAT), el filtro no encontrará nada — descargar el export EM-DAT correspondiente de public.emdat.be, o continuar sin EM-DAT y avisar al usuario
4. **Agrupar eventos en crisis** (año + departamento):
   - Los registros VIDECI son municipales — múltiples registros del mismo año+departamento son parte de la misma sequía
   - Agrupar por año + departamento → cada grupo es una "crisis departamental"
   - Calcular por grupo: nº eventos, municipios únicos, familias totales
   - Ejemplo: 632 registros de 2007 → 8 crisis departamentales (una por departamento afectado)
5. **Generar resumen estadístico** y presentar al usuario:
   - Total de registros y total de crisis (año+departamento)
   - Distribución por año (registros, crisis, municipios, familias)
   - Distribución por departamento
   - Totales de familias afectadas, hectáreas, ganado
   - Identificar periodos anómalos (si algún periodo tiene >3x el promedio de familias por evento)
   - Cobertura EM-DAT: qué crisis tienen match directo (año+departamento)
   - **Preguntar al usuario qué modo de verificación quiere**:
     - **Modo muestra**: seleccionar N eventos individuales y verificar municipio por municipio (Fase 2A → 3A)
     - **Modo completo**: verificar TODAS las crisis agrupadas, una fuente por año+departamento (Fase 2B → 3B)
     - **Modo híbrido**: primero completo (corroboración masiva), luego muestra granular para subir a verificado

---

## Fase 2A — Selección de Muestra (modo muestra)

Para verificación granular municipio por municipio.

1. **Determinar tamaño de muestra**: usar argumento del usuario o default 25
2. **Definir ejes de estratificación** (derivados de los datos, no hardcodeados):
   - **Periodo**: dividir el rango de años en terciles (temprano/medio/reciente)
   - **Severidad**: por `Fam. afec.` — pequeña (<P33), media (P33-P66), grande (>P66)
   - **Departamento**: asegurar cobertura de al menos los 5 departamentos más afectados
3. **Auto-detectar periodos para sobremuestreo**: si algún periodo tiene >3x el promedio de familias-por-evento comparado con otros periodos, asignar 40% de la muestra ahí
4. **Distribuir la muestra** balanceando periodo × severidad × departamento
5. **Presentar la muestra al usuario** en formato tabla:

```
| ID | Año | Departamento | Provincia | Municipio | Fam.Afec | Severidad |
```

6. **ESPERAR aprobación del usuario** antes de continuar. El usuario puede:
   - Aprobar: "dale" / "looks good" / "va"
   - Modificar: "agrega más de Oruro" / "sube a 30" / "incluye ID 1234"
   - Rechazar: "nueva muestra" / "cambia los criterios"

---

## Fase 2B — Preparación de Crisis Agrupadas (modo completo)

Para verificación masiva de todo el dataset por crisis (año+departamento).

1. **Listar todas las crisis** (año + departamento) con estadísticas:

```
| Año | Departamento | Eventos | Municipios | Fam.Total | EM-DAT match? |
```

2. **Pre-clasificar con EM-DAT**:
   - Crisis con match EM-DAT → marcar como `corroborado_emdat` (ya tienen fuente local)
   - Crisis sin match EM-DAT → necesitan búsqueda web
   - Reportar: "X de Y crisis ya corroboradas por EM-DAT. Quedan Z para buscar en web."
3. **Presentar plan de verificación al usuario**:
   - Total de crisis: N
   - Ya corroboradas por EM-DAT: X
   - Pendientes de búsqueda web: Z
   - Agentes necesarios estimados: ceil(Z / 5)
4. **ESPERAR aprobación del usuario** antes de continuar

---

## Fase 3 — Verificación por Agentes (en paralelo)

### Optimización de tokens

Los agentes son la operación más costosa. Aplicar estas reglas para minimizar tokens:

1. **Modelo**: usar `model: "haiku"` para todos los agentes (búsqueda+extracción, no necesitan sonnet)
2. **EM-DAT filtrado**: inyectar SOLO registros EM-DAT cuyos años coincidan con el cluster del agente, no el dataset completo
3. **Jerarquía filtrada**: de `source-hierarchies.yml`, enviar SOLO la sección del tipo detectado (ej: `sequia`), no todos los tipos
4. **Schema externo**: NO incluir el JSON schema inline — referenciar el archivo. Los agentes leen el schema desde:
   - Muestra: `.claude/skills/videci-verify/agent-schema-muestra.json`
   - Completo: `.claude/skills/videci-verify/agent-schema-completo.json`
5. **Reglas externas**: NO repetir reglas de clasificación/Wayback/IA inline — referenciar:
   - `.claude/skills/videci-verify/agent-reference.md` (reglas, Wayback, IA, EM-DAT usage)
6. **Patrones compactos**: enviar solo `nombre` y `patrones_busqueda` de cada nivel, omitir `notas`

### Cargar jerarquía de fuentes

Leer `source-hierarchies.yml`. Extraer SOLO la sección del tipo detectado en Fase 1. Preparar versión compacta (solo nombre + patrones por nivel, sin notas).

### Estructura del prompt de agente

El prompt de cada agente tiene 3 secciones:

1. **Datos del cluster** — eventos/crisis asignados (varía por agente)
2. **Contexto compacto** — inline, mínimo:
   ```
   Tipo de evento: {tipo}. Buscar en español e inglés.

   ## EM-DAT (match automático → "corroborado")
   [SOLO registros EM-DAT que cubren años de ESTE cluster]
   Si match año+depto: url="https://public.emdat.be/", titulo="EM-DAT {DisNo}", nivel_geo="departamento"
   Sigue buscando web para subir a "verificado" (municipio). Sin web mejor, EM-DAT = "corroborado".

   ## Fuentes (buscar en orden)
   [Niveles de source-hierarchies.yml para el {tipo} detectado — solo nombre + 1 patrón clave por nivel,
    con {tipo} ya sustituido. Ejemplo para sequía:
    1. Decretos: "Bolivia decreto emergencia sequía {year} {department}"
    2. ReliefWeb: "site:reliefweb.int Bolivia drought {year} {department}" (ADVERTENCIA: 403, solo WebSearch)]

   NO vincular fuentes de año incorrecto. Año fuente DEBE = año evento (±1 = corroborado_debil).
   ```
3. **Referencias a archivos** — el agente lee si necesita. Usar rutas ABSOLUTAS en el prompt (los agentes pueden no compartir el cwd del vault):
   ```
   Para reglas completas de clasificación, Wayback, Internet Archive: leer {vault}/.claude/skills/videci-verify/agent-reference.md
   Para schema de respuesta JSON: leer {vault}/.claude/skills/videci-verify/agent-schema-{modo}.json
   ```

### Fase 3A — Verificación por Muestra (modo muestra)

Muestra de Fase 2A. Busca fuente a nivel **municipio** por evento.

#### Agrupamiento

Clusters por año+departamento. Si cluster >8 eventos, subdividir por provincia. Objetivo: 3-6 agentes, 3-8 eventos c/u.

#### Prompt muestra

```
Verificador VIDECI Bolivia. Verificar cada evento a nivel MUNICIPIO.

## Cluster: {year}_{department}
[ID | año | depto | provincia | municipio | familias]

{CONTEXTO COMPACTO — con EM-DAT filtrado solo a años de este cluster}

## Instrucciones
1. Check EM-DAT match (año+depto) → fuente base
2. Buscar web por jerarquía, buscar MUNICIPIO nombrado
3. Municipio encontrado → "verificado". Solo depto → "corroborado". Nada → "no_verificado"
4. Buscar en ESPAÑOL e INGLÉS

Reglas y schema: leer {vault}/.claude/skills/videci-verify/agent-reference.md y agent-schema-muestra.json
Responder SOLO JSON válido.
```

#### Ejecución

Spawn todos con `model: "haiku"` en un solo mensaje (paralelo).

---

### Fase 3B — Verificación Completa por Crisis (modo completo)

Todas las crisis (año+departamento). **Una fuente por crisis**.

#### Pre-clasificación automática

1. Crisis con match EM-DAT → `corroborado_emdat` (ya tienen fuente, no enviar a agentes)
2. Solo enviar crisis SIN match EM-DAT

#### Agrupamiento

Por año/periodo. Objetivo: 3-8 agentes, 10-25 crisis c/u.

#### Prompt completo

```
Verificador de crisis VIDECI Bolivia ({tipo}). UNA fuente por crisis (año+departamento).

## Crisis asignadas
[año | depto | nº eventos | nº municipios | familias total]

{CONTEXTO COMPACTO — con EM-DAT filtrado solo a años de este cluster}

## Instrucciones
1. Buscar UNA fuente que confirme {tipo} en depto+año
2. Seguir jerarquía en orden
3. Fuente cubre TODOS los eventos VIDECI de esa crisis
4. Si fuente lista municipios → anotar en `municipios_nombrados`
5. Fuente multi-departamento del mismo año → reutilizar (misma URL, diferente crisis)

Techo: "corroborado" (departamento). Municipios nombrados → orquestador promueve a "verificado".
Reglas y schema: leer {vault}/.claude/skills/videci-verify/agent-reference.md y agent-schema-completo.json
Responder SOLO JSON válido.
```

#### Ejecución

Spawn todos con `model: "haiku"` en un solo mensaje (paralelo).

---

### Fase 3C — Modo Híbrido (completo → muestra)

Dos pasadas:

1. **Pasada 1**: Fase 3B → corroboración masiva
2. **Resultados intermedios**: cobertura alcanzada, candidatos a promoción
3. **Pasada 2**: usuario elige crisis/eventos para verificación granular (Fase 3A)
   - Sugerir: crisis con `municipios_nombrados` (candidatos promoción)
   - Sugerir: crisis grandes sin fuente
4. Agentes pasada 2 reciben fuentes de pasada 1 como contexto → no repiten búsquedas

#### Promoción de eventos

Si fuente de crisis nombró municipios:
- Cruzar `municipios_nombrados` vs municipios VIDECI de esa crisis
- Match → promover a `verificado` automáticamente
- Reportar: "X eventos promovidos a verificado por municipios nombrados"

---

## Fase 4 — Auditoría del Orquestador

Después de recibir los resultados JSON de todos los agentes:

### Validación mecánica (reglas duras)

Para cada fuente en cada evento/crisis:

1. **Auditoría de año**: si `año_fuente != año_evento`:
   - Diferencia > 1 año → **rechazar fuente**, no contar para clasificación
   - Diferencia == 1 año → aceptar solo como `corroborado_debil`
2. **Auditoría de tipo**: si `coincide_tipo_evento: false` → **rechazar fuente**
3. **Auditoría de geo**: `nivel_geo` determina techo de clasificación:
   - `municipio` → elegible para `verificado`
   - `provincia` o `departamento` → máximo `corroborado`
   - `pais` → máximo `corroborado_debil`
4. **Año no confirmado**: si `año_confirmado: false` → **marcar para revisión humana**
5. **Verificación de enlaces archivados**: si `archivada: true`, verificar que `url` sea una URL válida de `web.archive.org`. Marcar en alertas: "Fuente rescatada de Wayback Machine (original: {url_original})"

### Verificación independiente de fechas (OBLIGATORIA antes de Fase 5/6)

Los agentes pueden fabricar `año_fuente` (verificado en corridas reales: ~15% de las URLs no-EM-DAT tenían año inventado). El orquestador DEBE re-verificar la fecha de publicación real de CADA URL no-EM-DAT antes de generar productos o publicar en Wikidata:

1. Recopilar las URLs únicas de todas las fuentes de agentes (excluir `public.emdat.be`)
2. Para cada una, obtener la fecha real: fetch directo buscando `datePublished`/dateline; si el sitio bloquea (ReliefWeb da 403), usar Wayback (`archive.org/wayback/available` → fetch del snapshot → buscar "Originally published"/`datetime=`); último recurso CDX (`web.archive.org/cdx/search/cdx`)
3. Comparar con `año_fuente` declarado. Mismatch → re-aplicar reglas duras (rechazar/degradar) sobre TODAS las crisis que usan esa URL
4. Ojo con **análisis retrospectivos** (informes de Banco Mundial, papers): aunque su fecha sea plausible, no corroboran un año concreto salvo atribución explícita año+departamento
5. Reportar al usuario las fuentes caídas en esta pasada igual que las de la validación mecánica

### Promoción por municipios nombrados (modo completo y híbrido)

Si una fuente de crisis incluye `municipios_nombrados`:
1. Cruzar contra la lista de municipios VIDECI de esa crisis (año+departamento)
2. Eventos cuyo municipio aparece en `municipios_nombrados` → promover a `verificado`
3. El resto de eventos de esa crisis permanece en `corroborado`
4. Reportar: "X eventos promovidos a verificado (municipio nombrado en fuente de crisis)"

### Reclasificación

Después de rechazar fuentes inválidas, reclasificar cada evento según las fuentes restantes. Un evento puede bajar de categoría pero nunca subir.

### Propagación de estado (modo completo)

En modo completo, el estado de una crisis se propaga a TODOS los eventos VIDECI de ese año+departamento:
- Crisis `corroborado` → todos sus eventos son `corroborado` (excepto los promovidos a `verificado`)
- Crisis `no_verificado` → todos sus eventos son `no_verificado`
- `corroborado_emdat` (Fase 2B) mapea a `corroborado` en la propagación y en el CSV, con EM-DAT como fuente (url="https://public.emdat.be/", titulo="EM-DAT {DisNo}")
- Generar CSV enriquecido con TODOS los registros del dataset, no solo la muestra

### Presentar resultados al usuario

Mostrar:
- Tabla resumen con conteos por estado (eventos individuales, no crisis)
- En modo completo: cobertura total del dataset (N/{total} eventos verificados/corroborados)
- Fuentes rechazadas por la auditoría (si las hay) con motivo
- Eventos marcados para revisión humana
- En modo híbrido: sugerir crisis para pasada 2 granular
- Preguntar si el usuario quiere revisar algún evento específico

---

## Fase 5 — Generación de Productos

Generar los productos que el usuario solicite. Opciones disponibles (el usuario elige cuáles):

### 1. Nota de investigación (Markdown)

- Invocar `/obsidian-markdown` antes de crear
- Guardar en `Research/VIDECI Verificación {Tipo} - {YYYY-MM-DD}.md`
- Estructura:
  - Frontmatter con tags, fecha, estado
  - Metodología (muestra, estratificación, fuentes)
  - Resultados por periodo (cada evento con estado, fuentes vinculadas, notas de auditoría)
  - Resumen con tabla de conteos
  - Evaluación general
  - Fuentes clave
- Correr Connection Discovery después de crear

### 2. HTML interactivo

- Guardar en `Research/videci-verificacion-{tipo}-{fecha}.html`
- Auto-contenido, sin dependencias externas
- Incluir:
  - Barra de estadísticas con conteos por estado
  - Barra de progreso visual de credibilidad
  - Tarjetas expandibles por evento con fuentes vinculadas
  - Filtros por estado, periodo, severidad, departamento
  - Sección de observaciones clave
  - Jerarquía de confiabilidad de fuentes
  - Tema oscuro

### 3. CSV enriquecido

- Guardar en `Research/videci-verificacion-{tipo}-{fecha}.csv`
- Columnas adicionales al CSV original:
  - `estado_verificacion`: verificado / corroborado / corroborado_debil / no_verificado
  - `fuente_url`: URL de la mejor fuente encontrada
  - `fuente_titulo`: título de la fuente
  - `fuente_año`: año de publicación de la fuente
  - `coincide_año`: true/false
  - `coincide_tipo`: true/false
  - `nivel_geo`: municipio / provincia / departamento / pais
  - `fuente_archivada`: true/false — si la fuente fue rescatada de Wayback Machine
  - `fuente_url_original`: URL original (solo si archivada)
  - `alertas`: notas de auditoría
  - `crisis_id`: identificador de crisis año+departamento (ej: "2007_La Paz")
  - `promovido`: true/false — si fue promovido a verificado por municipio nombrado en fuente de crisis
- **Modo muestra**: solo eventos de la muestra
- **Modo completo/híbrido**: TODOS los registros del dataset con estado propagado desde crisis

### 4. Nota en español (traducción)

- Si el usuario la solicita, crear versión en español de la nota markdown
- Guardar en `Research/VIDECI Verificación {Tipo} (ES) - {YYYY-MM-DD}.md`

### 5. Batch de Wikidata

- Si el usuario lo solicita → Fase 6

---

## Fase 6 — Publicación en Wikidata (opt-in)

Genera un batch de QuickStatements para crear/actualizar items de Wikidata con las crisis verificadas. **Solo cuando el usuario lo pide explícitamente.** Referencia completa (QIDs verificados, propiedades, sintaxis, política): `wikidata-reference.md` en este directorio. Cargar también el skill `/wikidata` si hay que resolver QIDs no cubiertos por la referencia.

1. **Filtrar crisis publicables**: solo `verificado` y `corroborado` (incluye `corroborado_emdat`). Granularidad = crisis departamental, nunca registros municipales individuales.
2. **Reconciliar contra Wikidata** (obligatorio, evita duplicados):
   - SPARQL: items existentes de ese tipo de desastre en Bolivia (query en `wikidata-reference.md`), filtrar por año localmente
   - Complementar con `wbsearchentities` en es/en por crisis sin match
   - Clasificar cada crisis: **crear** (sin match) / **actualizar** (item existente, añadir statements+referencias faltantes) / **enriquecer item nacional** (existe item del año sin desglose departamental)
3. **Presentar plan al usuario** y ESPERAR aprobación:

```
| Año | Departamento | Estado | Acción | Item existente | Fuente para referencia |
```

   - El usuario puede excluir crisis, cambiar acciones, o pedir solo-actualizaciones (sin CREATE)
4. **Generar el batch** en `Research/videci-wikidata-{tipo}-{fecha}.qs`:
   - Sintaxis V1 según `wikidata-reference.md` (TABs reales, labels es+en, fechas con precisión, referencia S854+S813 en cada statement sustantivo)
   - QIDs de tipo y departamento: usar la tabla verificada de la referencia; cualquier QID/PID no tabulado se resuelve en runtime con `wbsearchentities` y se confirma con el usuario — NUNCA adivinar
5. **Entregar instrucciones de ejecución**: el usuario corre el batch en quickstatements.toolforge.org con su cuenta (preview primero; batches >100 items: muestra de 5-10 antes del resto; reversible vía EditGroups). **Este skill nunca ejecuta ediciones en Wikidata directamente.**
6. **Reportar**: crisis incluidas/excluidas, creates vs updates, y añadir enlace al `.qs` y al batch de EditGroups (cuando exista) en la nota de investigación

---

## Notas de Comportamiento

- **Idioma**: toda comunicación con el usuario y todos los productos en español. Los agentes buscan fuentes en español e inglés.
- **Siempre esperar aprobación** de la muestra antes de lanzar agentes.
- **Spawn agentes en un solo mensaje** (paralelo, no secuencial).
- **Nunca confiar ciegamente en los agentes** — la auditoría del orquestador (Fase 4) es obligatoria.
- **Presentar fuentes rechazadas** al usuario — la transparencia sobre errores encontrados aumenta la confianza en los resultados.
- Si algún agente falla o devuelve JSON inválido, reportar al usuario y ofrecer re-ejecutar ese cluster.
- El usuario puede pedir verificación más profunda de eventos específicos después de ver los resultados.
