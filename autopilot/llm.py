"""Schlanker Client für OpenAI-kompatible Endpunkte (Ollama /v1, llama-server /v1).

Bewusst ohne LangChain: weniger Abhängigkeiten, volle Kontrolle, und derselbe
Endpunkt wie OpenCode -> Ollama lädt das Modell nicht neu (gleicher Kontext).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import httpx

from config import SETTINGS

THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.S | re.I)
FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)
VERDICT_RE = re.compile(r"verdict\W{0,4}(PASS|FAIL)", re.I)


class LLMError(RuntimeError):
    pass


def strip_thinking(text: str) -> str:
    text = THINK_BLOCK_RE.sub("", text or "")
    if "</think>" in text.lower():          # öffnendes Tag fehlte (manche Templates)
        text = re.split(r"</think>", text, flags=re.I)[-1]
    return text.strip()


def chat(system: str, user: str, max_tokens: int = 12000) -> str:
    payload = {
        "model": SETTINGS.llm_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        r = httpx.post(
            f"{SETTINGS.llm_base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {SETTINGS.llm_api_key}"},
            timeout=httpx.Timeout(SETTINGS.llm_timeout_s, connect=15),
        )
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise LLMError(f"LLM-Aufruf fehlgeschlagen: {e}") from e
    content = strip_thinking(msg.get("content") or "")
    if not content:
        raise LLMError("LLM lieferte leere Antwort (evtl. max_tokens durch Thinking aufgebraucht)")
    return content


def ping() -> tuple[bool, str]:
    try:
        r = httpx.get(f"{SETTINGS.llm_base_url}/models", timeout=10,
                      headers={"Authorization": f"Bearer {SETTINGS.llm_api_key}"})
        r.raise_for_status()
        ids = [m.get("id") for m in r.json().get("data", [])]
    except Exception as e:  # noqa: BLE001
        return False, f"{SETTINGS.llm_base_url} nicht erreichbar: {e}"
    if SETTINGS.llm_model not in ids:
        return False, f"Modell '{SETTINGS.llm_model}' nicht gefunden. Verfügbar: {ids}"
    return True, "ok"


def extract_json(text: str) -> dict | None:
    """Letztes gültiges JSON-Objekt aus einer Modellantwort holen."""
    text = strip_thinking(text)
    for block in reversed(FENCE_RE.findall(text)):
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass
    found: dict | None = None
    i = 0
    while i < len(text):                  # alle Top-Level-Objekte prüfen, das letzte mit "verdict" gewinnt
        if text[i] != "{":
            i += 1
            continue
        depth, in_str, esc, end = 0, False, False, -1
        for e in range(i, len(text)):
            ch = text[e]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = e
                    break
        if end < 0:
            break
        try:
            obj = json.loads(text[i:end + 1])
            if isinstance(obj, dict) and "verdict" in {k.lower() for k in obj}:
                found = obj
        except json.JSONDecodeError:
            pass
        i = end + 1
    if found is not None:
        return found
    return None


@dataclass
class Verdict:
    verdict: str                      # "PASS" | "FAIL"
    summary: str = ""
    issues: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    parsed: bool = True

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    def as_feedback(self) -> str:
        lines = [f"Urteil: {self.verdict} – {self.summary}".rstrip(" –")]
        lines += [f"- {i}" for i in self.issues]
        return "\n".join(lines)


def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    return [str(x) for x in v if str(x).strip()]


def parse_verdict(text: str) -> Verdict:
    obj = extract_json(text)
    if obj:
        low = {k.lower(): v for k, v in obj.items()}
        v = str(low.get("verdict", "")).strip().upper()
        verdict = "PASS" if v == "PASS" else "FAIL"
        issues = _as_list(low.get("issues"))
        if verdict == "FAIL" and not issues:
            issues = ["Reviewer meldete FAIL ohne konkrete Punkte – Akzeptanzkriterien erneut einzeln prüfen."]
        return Verdict(verdict, str(low.get("summary", "")), issues, _as_list(low.get("hints")))
    matches = VERDICT_RE.findall(strip_thinking(text))
    if matches:
        verdict = matches[-1].upper()
        return Verdict(verdict, "(ohne JSON geantwortet)", [] if verdict == "PASS" else [strip_thinking(text)[-1500:]], parsed=False)
    return Verdict("FAIL", "Review-Antwort nicht auswertbar", ["Antwort enthielt kein Urteil; Review wird wiederholt."], parsed=False)
