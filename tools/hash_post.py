#!/usr/bin/env python3
"""Imprime a 'impressão digital' de um post (telas + legenda + vídeo), para saber se mudou depois de agendado.
Uso: python3 tools/hash_post.py post.json"""
import hashlib, json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))
base = json.dumps({"slides": p.get("slides", []), "legenda": p.get("legenda", ""), "pronto": p.get("pronto", "")}, sort_keys=True, ensure_ascii=False)
print(hashlib.sha1(base.encode("utf-8")).hexdigest()[:16])
