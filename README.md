# videci-verify

Skill de [Claude Code](https://claude.com/claude-code) que verifica los registros de desastres del sistema VIDECI (Viceministerio de Defensa Civil de Bolivia) contra fuentes independientes, usando agentes de búsqueda en paralelo con una auditoría obligatoria antes de aceptar cualquier hallazgo.

## El problema

VIDECI mantiene miles de registros municipales de desastres (sequías, inundaciones, heladas, granizadas) acumulados desde 2002. Son demasiados para revisar a mano, y no hay garantía de que cada uno corresponda a un evento real, documentado en algún otro lugar.

## Qué hace

1. **Agrupa** los registros municipales en "crisis" (año + departamento).
2. **Reparte el trabajo** entre varios agentes en paralelo, cada uno buscando evidencia independiente por su lote de crisis — decretos oficiales, informes de organismos internacionales (FAO, PMA, Cruz Roja), el Instituto del Seguro Agrario (INSA), prensa boliviana, y EM-DAT cuando aplica.
3. **Clasifica** cada evento en `verificado` / `corroborado` / `corroborado_débil` / `no_verificado` según qué tan específica y confiable sea la evidencia encontrada.
4. **Audita** cada fuente citada por los agentes antes de aceptarla — verifica de forma independiente la fecha real de publicación, el tipo de evento y el lugar. Los agentes de búsqueda fabrican fuentes con más frecuencia de la que uno esperaría: en corridas reales se detectaron artículos con año de publicación incorrecto atribuido, decretos citados con contenido que no tienen, y hasta un PDF completamente ajeno al tema presentado como evidencia.
5. **Produce** una nota de investigación, un reporte HTML interactivo, un CSV enriquecido con el estado y la fuente de cada registro, y — opcionalmente, solo si el usuario lo pide explícitamente — un batch para publicar los eventos confirmados en [Wikidata](https://www.wikidata.org).

Corre en tres modos: **muestra** (verificación granular municipio por municipio de una selección estratificada), **completo** (todas las crisis del dataset, una fuente por crisis), o **híbrido** (completo primero, luego muestra granular sobre lo que quedó corroborado).

## Estructura

| Archivo | Contenido |
|---|---|
| `SKILL.md` | Definición completa del skill — las 6 fases del proceso, desde lectura del CSV hasta publicación en Wikidata |
| `agent-reference.md` | Reglas de clasificación, uso de Wayback Machine/Internet Archive, y convenciones de EM-DAT que los agentes leen en tiempo de ejecución |
| `agent-schema-muestra.json` / `agent-schema-completo.json` | Schemas de respuesta JSON que los agentes deben seguir, según el modo |
| `source-hierarchies.yml` | Jerarquía de fuentes y patrones de búsqueda por tipo de desastre (sequía, inundación, granizada, helada, incendio, deslizamiento) |
| `wikidata-reference.md` | QIDs/PIDs verificados, sintaxis de QuickStatements, y la consulta SPARQL de reconciliación para la Fase 6 (publicación opcional) |
| `scripts/publish_wikidata.py` | Publicador vía API directa de Wikidata (`wbeditentity`) — alternativa a QuickStatements, idempotente y resumible, usado para el batch de inundaciones |

## Uso

Se invoca desde Claude Code con un CSV de VIDECI:

```
/videci-verify ruta/al/archivo.csv [tamaño_muestra] [modo]
```

La orquestación corre en la conversación principal — el usuario ve y aprueba cada paso (la muestra antes de verificarla, el plan antes de lanzar agentes, el batch de Wikidata antes de generarlo). Los agentes hacen el trabajo pesado de búsqueda.

## Estado

Usado para verificar los datasets de sequía (2002–2023), inundación (2002–2023) y granizada (2002–2023) de Bolivia. El batch de inundaciones ya se publicó en Wikidata vía la API directa.
