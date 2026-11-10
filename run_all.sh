#!/usr/bin/env bash
# Corre todos los modelos: los de API en dos filas en paralelo (Google y Groq), después los locales.
cd "$(dirname "$0")"
PY=.venv/bin/python
( for m in gemini-3.5-flash gemini-3.5-flash-lite gemma4-31b; do echo "=== $m"; $PY -u gt.py run --model $m; done ) > logs_google.txt 2>&1 &
( echo "=== qwen3.8-27b-groq"; $PY -u gt.py run --model qwen3.8-27b-groq ) > logs_groq.txt 2>&1 &
( export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH
  for m in gemma4-12b qwen3.5-9b; do
    tag=$($PY -c "import json,sys; print({x['name']:x for x in json.load(open('models.json'))['models']}[sys.argv[1]]['model'])" $m)
    ollama pull $tag > /dev/null 2>&1; echo "=== $m"; $PY -u gt.py run --model $m
  done ) > logs_local.txt 2>&1 &
wait
$PY gt.py report > /dev/null && echo LISTO > logs_fin.txt
