# Agent Reference — Classification Rules & Tools

<!-- In English intentionally: compact reference for search agents that query in both languages. User-facing output stays in Spanish. -->

## Classification Rules (STRICT)

- **verificado**: source with `coincide_año: true` AND `coincide_tipo_evento: true` AND `nivel_geo: municipio`
- **corroborado**: source with `coincide_año: true` AND `coincide_tipo_evento: true` AND `nivel_geo: departamento` or `provincia` (or EM-DAT match)
- **corroborado_debil**: source with year ±1 OR only country-level match
- **no_verificado**: no valid source found at any level

Source year MUST match event year (±1 max for corroborado_debil). Wrong disaster type = reject source entirely.

## Source Validation Checklist

For EACH source found:
1. Extract publication year → compare with event year
2. Confirm disaster type matches (sequía ≠ inundación)
3. Determine geographic match level: municipio > provincia > departamento > país
4. If URL returns 404/403 → try Wayback rescue (section below)

## Date Verification (MANDATORY — do not skip)

NEVER report `año_fuente` from a search-result snippet alone. A snippet mentioning "{year}" does not mean the source was published in {year}. Verified failure modes from past runs: a 2007 El Niño report cited for 2002, a 2007 UNICEF story cited for 2016, a December-2017 World Bank *historical analysis* cited as corroboration of 2017 events, a 2026 news article cited for 2023.

Before reporting ANY source:
1. **Fetch the page and read its publication date** (ReliefWeb: "Originally published"; news: dateline/`datePublished`). If the site blocks fetching (403), fetch the Wayback snapshot instead: `https://web.archive.org/web/2024/{url}` and read the date there.
2. **Set `año_fuente` = year of the EVENT the source describes**, not the publication year, when they differ (e.g., a Feb-2022 article about Dec-2021 floods → the event year is what matters; note both in `notas`).
3. **Reject analyses/retrospectives**: a report that *analyzes* historical disasters (World Bank studies, academic papers) does NOT corroborate any specific year's event unless it explicitly attributes impacts to that year+department.
4. If you cannot confirm the date by reading the page or its archive → report the crisis as `no_verificado` rather than guessing. A wrong source is worse than no source: the orchestrator audits dates against Wayback/CDX and fabricated years invalidate the whole cluster's credibility.

## Wayback Machine (broken link rescue)

Only when a found URL returns 404/403:
1. Check: `https://archive.org/wayback/available?url={URL_ENCODED}`
2. If `archived_snapshots.closest.available == true` → use archived URL
3. Mark: `"archivada": true`, `"url_original": "{ORIGINAL}"`

Rate limit: max 1 request/second to archive.org.

Coverage: GOOD for PDFs, reliefweb.int, fao.org. BAD for insa.gob.bo/95-prensa/*, bolivia.com old news.

## Internet Archive CLI (last resort, pre-2010 events)

```bash
ia search 'subject:"Bolivia" subject:"drought" date:[{year}-01-01 TO {year}-12-31] mediatype:texts' --parameters="rows=10"
ia search -F '"sequía" "{municipality}" "{year}"' --parameters="rows=5"
```

Documents at archive.org have permanent URLs. Include identifier: "details/{identifier}".

If the `ia` CLI is not installed (`which ia` fails), skip this level — do not attempt to install it.

## EM-DAT Usage

EM-DAT data is pre-loaded in your prompt. If event matches year+department → automatic `corroborado`. To reach `verificado`, find a web source naming the specific municipality.
