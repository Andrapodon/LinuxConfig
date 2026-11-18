#!/usr/bin/env python3
"""Batch-classify Paperless-ngx documents with Gemini and update metadata."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

DEFAULT_MODEL = "models/gemini-flash-latest"


def call_ai(ocr_text: str, api_key: str, model_name: str) -> dict | None:
    prompt = (
        "You are a data extraction assistant. Given this OCR text, output ONLY a valid JSON object "
        "with keys: 'title' (format exactly YYYY-MM-DD - Correspondent - Subject), "
        "'correspondent' (Name of the company/sender), "
        "'document_type' (Pick one exact match: Rechnung / Quittung, Garantieschein, Versicherungspolice, "
        "Lohnausweis & Steuerbeleg, Behördenbrief, Vertrag, Medizinisches Dokument, or null), "
        "'tag' (Pick one exact match: Arbeit & Bildung, Finanzen & Vorsorge, Wohnen, Elektronik, Gesundheit, or null). "
        "Do not use markdown blocks, output raw JSON. TEXT: " + ocr_text[:3000]
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
        method="POST",
    )

    last_err = ""
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                data = json.loads(response.read().decode())
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```json"):
                    text = text[7:-3]
                elif text.startswith("```"):
                    text = text[3:-3]
                return json.loads(text.strip())
        except Exception as exc:
            last_err = str(exc)
            time.sleep(2)
    print(f" (AI Error: {last_err}) ", end="", flush=True)
    return None


def process_user(base_url: str, username: str, token: str, api_key: str, model_name: str) -> None:
    print(f"\n--- Processing {username} ---", flush=True)
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json", "Accept": "application/json"}
    id_cache: dict[str, dict[str, int]] = {"tags": {}, "document_types": {}, "correspondents": {}}

    def get_id(endpoint: str, name: str | None) -> int | None:
        if not name or name == "null":
            return None
        if name in id_cache[endpoint]:
            return id_cache[endpoint][name]
        query = urllib.parse.urlencode({"name__iexact": name})
        req = urllib.request.Request(f"{base_url}/{endpoint}/?{query}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data["count"] > 0:
                    id_cache[endpoint][name] = data["results"][0]["id"]
                    return data["results"][0]["id"]
        except Exception:
            pass
        return None

    unvollstaendig_id = get_id("tags", "Unvollständig")

    docs = []
    url: str | None = f"{base_url}/documents/"
    while url:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode())
                docs.extend(data["results"])
                url = data.get("next")
        except Exception:
            break

    print(f"Found {len(docs)} total docs for {username}.", flush=True)
    for i, doc in enumerate(docs):
        doc_title = doc["title"]
        print(f"[{i + 1}/{len(docs)}] {doc_title[:30]}... ", end="", flush=True)
        ocr = doc.get("content", "")
        if not ocr:
            print("Skip (No OCR)", flush=True)
            continue

        ai_data = call_ai(ocr, api_key=api_key, model_name=model_name)
        if not ai_data:
            print("Skip (AI Timeout/Fail)", flush=True)
            continue

        payload: dict[str, object] = {"title": ai_data.get("title", doc_title)}
        is_incomplete = False

        dt_id = get_id("document_types", ai_data.get("document_type"))
        if dt_id:
            payload["document_type"] = dt_id
        else:
            is_incomplete = True

        tag_id = get_id("tags", ai_data.get("tag"))
        tags_list = [tag_id] if tag_id else []

        corr = ai_data.get("correspondent")
        if corr and corr != "null":
            corr_id = get_id("correspondents", corr)
            if corr_id:
                payload["correspondent"] = corr_id
            else:
                is_incomplete = True
        else:
            is_incomplete = True

        if is_incomplete and unvollstaendig_id:
            tags_list.append(unvollstaendig_id)
        payload["tags"] = tags_list

        req = urllib.request.Request(
            f"{base_url}/documents/{doc['id']}/",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                inc_str = " (Unvollständig)" if is_incomplete else ""
                print(f"OK -> {payload['title']}{inc_str}", flush=True)
        except Exception as exc:
            print(f"Update Failed: {exc}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("PAPERLESS_URL", ""), help="Paperless API base URL (or PAPERLESS_URL env)")
    parser.add_argument("--user", default=os.environ.get("PAPERLESS_USER", "Marc"), help="Display name for log output")
    parser.add_argument("--token", default=os.environ.get("PAPERLESS_TOKEN", ""), help="Paperless API token (or PAPERLESS_TOKEN env)")
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    base_url = args.url.rstrip("/")
    token = args.token

    if not api_key or not base_url or not token:
        print(
            "Error: GEMINI_API_KEY, PAPERLESS_URL (--url), and PAPERLESS_TOKEN (--token) must be set.\n"
            "Tip: pass them via `pass-cli run` or environment variables.",
            file=sys.stderr,
        )
        return 1

    print(f"Using Model: {args.model}", flush=True)
    process_user(base_url=base_url, username=args.user, token=token, api_key=api_key, model_name=args.model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
