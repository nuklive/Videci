#!/usr/bin/env python3
"""
Publica payloads VIDECI en Wikidata via wbeditentity (API directa, no QuickStatements).

Uso:
  python publish_wikidata.py <dryrun.json> <publicados.json> [--live] [--hashtag "#videci-tag"]

- Sin --live: solo valida el archivo de payloads y reporta cuántos faltan por publicar.
- Con --live: publica los que falten (los que ya están en publicados.json se saltan).

Formato esperado de <dryrun.json>:
  {"payloads": [{"año": 2002, "accion": "create"|"update", "qid": "Q..." (si update),
                 "entity_data": {...wbeditentity data...}}, ...]}

Formato de <publicados.json>: {"<clave>": "Q...", ...} — se actualiza tras CADA publicación
exitosa, así que si el script se corta a medias, re-correrlo continúa donde quedó.

Credenciales: ~/.config/wikidata/.env con WIKIDATA_BOT_USER y WIKIDATA_BOT_PASSWORD
(bot password de Special:BotPasswords, no la contraseña normal de la cuenta).
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

API = "https://www.wikidata.org/w/api.php"
ENV_PATH = Path.home() / ".config" / "wikidata" / ".env"
USER_AGENT = "videci-verify-bot/1.0 (Obsidian vault research tool)"


def load_env():
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def login(session, user, password):
    r = session.get(API, params={
        "action": "query", "meta": "tokens", "type": "login", "format": "json",
    })
    login_token = r.json()["query"]["tokens"]["logintoken"]

    r = session.post(API, data={
        "action": "login", "lgname": user, "lgpassword": password,
        "lgtoken": login_token, "format": "json",
    })
    result = r.json().get("login", {}).get("result")
    if result != "Success":
        raise RuntimeError(f"Login falló: {r.json()}")


def get_csrf_token(session):
    r = session.get(API, params={
        "action": "query", "meta": "tokens", "type": "csrf", "format": "json",
    })
    return r.json()["query"]["tokens"]["csrftoken"]


def publish_one(session, csrf_token, payload, hashtag):
    data_json = json.dumps(payload["entity_data"], ensure_ascii=False)
    summary = f"VIDECI verify: {payload.get('accion', 'create')} {payload.get('año', '')} {hashtag}".strip()

    params = {
        "action": "wbeditentity",
        "data": data_json,
        "token": csrf_token,
        "bot": 1,
        "summary": summary,
        "format": "json",
        "maxlag": 5,
    }
    if payload.get("accion") == "update" and payload.get("qid"):
        params["id"] = payload["qid"]
    else:
        params["new"] = "item"

    r = session.post(API, data=params)
    result = r.json()

    if "error" in result:
        raise RuntimeError(f"wbeditentity error para {payload.get('año')}: {result['error']}")

    return result["entity"]["id"]


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    dryrun_path = Path(args[0])
    publicados_path = Path(args[1])
    live = "--live" in args
    hashtag = "#videci"
    if "--hashtag" in args:
        hashtag = args[args.index("--hashtag") + 1]

    payloads = json.loads(dryrun_path.read_text())["payloads"]
    publicados = json.loads(publicados_path.read_text()) if publicados_path.exists() else {}

    pendientes = [p for p in payloads if str(p["año"]) not in publicados]
    print(f"Total payloads: {len(payloads)} — ya publicados: {len(publicados)} — pendientes: {len(pendientes)}")

    if not live:
        print("Modo dry-run (sin --live). No se llamó a la API. Revisa los payloads pendientes antes de publicar.")
        for p in pendientes:
            print(f"  - {p['año']}: {p.get('accion')} — {p['entity_data']['labels']['es']['value']}")
        return

    env = load_env()
    user = env["WIKIDATA_BOT_USER"]
    password = env["WIKIDATA_BOT_PASSWORD"]

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    login(session, user, password)
    csrf_token = get_csrf_token(session)
    print(f"Login OK como {user}")

    for p in pendientes:
        año = str(p["año"])
        try:
            qid = publish_one(session, csrf_token, p, hashtag)
            publicados[año] = qid
            publicados_path.write_text(json.dumps(publicados, indent=1, ensure_ascii=False))
            print(f"  {año} → {qid} (guardado)")
        except Exception as e:
            print(f"  {año} → ERROR: {e}")
            print("  Deteniendo — corrige y re-corre, los ya publicados no se repiten.")
            sys.exit(1)
        time.sleep(1)

    print(f"Listo. {len(publicados)}/{len(payloads)} publicados.")


if __name__ == "__main__":
    main()
