# Änderungen an Setup und Dokumenten (Überarbeitung 09/2026)

Stand der Prüfung: 28.09.2026. Getestet wurde in einer Linux-Sandbox mit dem echten
OpenCode 1.18.33, echtem Git und npm sowie einem simulierten Modell-Server (die GPU-Inferenz
selbst konnte dort nicht laufen). Alles, was nicht getestet werden konnte, ist in der README
als „ungetestet“ markiert.

## 1. Orchestrierung

| Vorher | Jetzt | Warum |
|---|---|---|
| 4 verschiedene Modelle (qwen3:14b, qwen2.5-coder:14b, qwen3:8b, phi4-mini) | **ein Modell für alle Rollen**, auch `small_model` | Bei 12 GB VRAM und `MAX_LOADED_MODELS=1` erzwingt jede Delegation einen Modellwechsel samt Neuverarbeitung des Kontexts – mehrere pro Task. phi4-mini wurde nirgends sinnvoll genutzt. |
| Das 14B-Planner-Modell orchestriert den Ablauf per Tool-Calls | **deterministischer Ablauf im Python-Code** (Autopilot), LLM nur für begrenzte Einzelschritte | Kleine Modelle überspringen Schritte, markieren Tasks selbst als erledigt, und ihr Kontext wächst von Task zu Task. Der interaktive Planner-Modus bleibt zusätzlich erhalten. |
| Reviewer sehen nur den Textbericht des Coders | Reviewer bekommen **echten `git diff`** + Ergebnis von `scripts/check.sh` | Selbstauskünfte kleiner Modelle sind unzuverlässig. |
| Keine objektive Prüfung | neues Prüf-Gate **`scripts/check.sh`** (typecheck, lint, test, build) **vor** den LLM-Reviews | Billig, objektiv, und liefert dem Coder konkrete Fehlermeldungen. |
| Kein Rollback | Basis-Commit je Task; PASS → Commit, 3 Fehlversuche → Rollback + Patch + `blocked` | Autonomer Betrieb braucht einen sicheren Ausgangszustand für die nächste Task. |
| Quality-Reviewer kann bei jeder Kleinigkeit ablehnen | FAIL nur bei blockierenden Mängeln, Rest als `hints` in den Commit-Text | Verhindert Endlosschleifen durch Stil-Nörgelei. |
| Rollentrennung Spec → Quality | **beibehalten** | Die Trennung ist sinnvoll; fokussierte Prompts helfen kleinen Modellen. |
| Rollen-Prompts doppelt (OpenCode-MD + Python) | **eine Quelle**: der Autopilot liest die Prompts aus `.opencode/agents/*.md` | Keine auseinanderlaufenden Definitionen. |
| Freitext-Urteil „Verdict: PASS/FAIL“ | JSON-Urteil mit robustem Parser (Thinking-Blöcke, Codefences, Fallback) | Die alte Erkennung konnte auf `<think>`-Inhalte hereinfallen. |

## 2. Fehler im bisherigen Code und in der Konfiguration

**LangGraph-Skizze (`langgraph/`, jetzt ersetzt durch `autopilot/`)**
- Ein FAIL im Spec-Review erhöhte `revision_count` nicht. Folge: Endlosschleife Coder ↔
  Spec-Reviewer bis zum Rekursionslimit von LangGraph.
- `TASKS.md` wurde nie aktualisiert, dadurch wählte jeder Lauf erneut dieselbe Task.
- Der Coder hatte keinen Datei- oder Shell-Zugriff und erzeugte nur Text. Jetzt läuft der Coder
  über `opencode run --agent coder` mit echten Tools.
- Altes Review-Feedback blieb beim nächsten Versuch stehen und vermischte sich mit neuem.
- Der Ordnername `langgraph/` kann das gleichnamige Python-Paket überdecken (z. B. bei
  `python -m langgraph...`) und wurde deshalb zu `autopilot/`.
- `langchain-ollama` entfällt: Der Autopilot spricht denselben OpenAI-kompatiblen `/v1`-Endpunkt
  wie OpenCode. So gilt derselbe Kontext und Ollama lädt das Modell nicht neu; zudem funktioniert
  dadurch auch llama.cpp.

**OpenCode-Konfiguration** (im Test mit OpenCode 1.18.33 nachgewiesen)
- `opencode run --agent coder` mit `mode: subagent` fällt stillschweigend auf den
  Standard-Agenten zurück, deshalb hat der Coder jetzt `mode: all`.
- Rechte auf `ask` werden in `opencode run` automatisch abgelehnt **und beenden den Lauf**. Die
  Standardwerte für `.env`-Lesen, Doom-Loop und externe Verzeichnisse standen auf `ask`. Jetzt
  gibt es nur noch explizit `allow` oder `deny`; bei `deny` arbeitet das Modell weiter.
- Die alte `tools:`-Syntax ließ bei den Reviewern `task` (Subagenten starten) und `webfetch`
  offen, und der Planner durfte alle Dateien bearbeiten. Jetzt sind die Rechte pro Rolle mit
  Mustern gesetzt (getestet: `docs/sub/x.md` wird verweigert, `web/AGENTS.md` erlaubt).
- `temperature` pro Agent entfernt: Die Ollama-Modelle bringen die vom Hersteller empfohlenen
  Sampling-Werte mit. Eine niedrige Temperatur schadet Thinking-Modellen (Wiederholungsschleifen),
  und OpenCode 2 sendet den Wert ohnehin nicht.
- Kontextgrenzen (`limit.context = 65536`) pro Modell ergänzt. Ohne diese Angabe weiß OpenCode
  nicht, wann es verdichten muss, und Ollama schneidet stillschweigend ab.

**Setup**
- Der Kontext von 16k war zu klein: Laut Ollama gilt unter 24 GB VRAM ein Standard von 4k, und
  für Agenten werden mindestens 64k empfohlen. Jetzt 65 536, zusätzlich `OLLAMA_NUM_PARALLEL=1`.
- Node.js war als „optional“ beschrieben, ist aber Pflicht (Next.js). Docker/Postgres wird schon
  für die Entwicklung gebraucht, nicht erst fürs Hosting.
- Das `processors=12`-Limit in `.wslconfig` bremste den CPU-Anteil des Modells und wurde
  entfernt; `swap` wurde erhöht.
- Die Ollama-Einstellungen werden jetzt als Datei ins systemd-Verzeichnis kopiert
  (`scripts/ollama-override.conf`) statt im Editor eingetippt.
- Der ZIP- bzw. Ordnername in der README (`badminton-liga-agents`) passte nicht zum Paket
  (`Badminton_IHL`).
- In der ursprünglichen Struktur hätte Next.js im Projektroot mit `AGENTS.md`, `docs/` usw.
  kollidiert. Die App liegt jetzt in `web/`.

## 3. Modelle

| Rolle | Vorher | Jetzt |
|---|---|---|
| alle | qwen3:14b / qwen2.5-coder:14b / qwen3:8b / phi4-mini | **qwen3.6:35b** (Qwen3.6-35B-A3B) |
| Alternative | – | qwen3.5:9b (komplett im VRAM), Qwen3.6 via llama.cpp (optional) |

Begründung: Qwen3.6-35B-A3B ist ein MoE-Modell mit rund 3B aktiven Parametern, auf agentisches
Coding trainiert, mit Tool-Calls und 256K nativem Kontext. Durch die hybride Attention bleibt der
KV-Cache bei 64k unter 1 GB. Trotz teilweiser Auslagerung in den RAM ist es daher auf 12 GB VRAM
nutzbar und deutlich stärker als die bisherigen 8–14B-Modelle. qwen2.5-coder war außerdem in
Agenten-Harnesses für unzuverlässige Tool-Calls bekannt.

Ollama bietet keine gezielte Auslagerung der MoE-Experten. Deshalb gibt es optional ein
llama.cpp-Profil mit `--n-cpu-moe` (Anhang A der README, ungetestet).

## 4. Tech-Stack und Spezifikation

- **Auth.js → Better Auth.** Auth.js wird inzwischen vom Better-Auth-Team gepflegt, das für neue
  Projekte ausdrücklich Better Auth empfiehlt. Better Auth bringt E-Mail/Passwort,
  Passwort-Reset, Rate-Limiting und einen Drizzle-Adapter mit, also weniger sicherheitskritischen
  Eigenbau für ein lokales Modell.
- Versionen konkretisiert (Stand heute): Next.js 16, Tailwind 4, Postgres 17, Vitest, Zod.
- `docs/PROJECT_SPEC.md` wurde nur minimal und gekennzeichnet angepasst: Zuordnung
  `players` ↔ Better-Auth-Tabelle `user`, zusätzliche Tabelle `invitations`, scrypt als
  zulässiges Hashing, Hinweis zur manuellen 375-px-Prüfung. **Fachlich ist nichts verändert.**
- `AGENTS.md` wurde gekürzt (sie steckt in jedem Prompt) und um Repo-Struktur, Befehle und harte
  Regeln ergänzt: nicht-interaktive Befehle, kein Dev-Server, Fachlogik als reine Funktionen in
  `src/domain/`.

## 5. Backlog (`TASKS.md`)

Statt 8 grober Platzhalter gibt es jetzt 32 kleine Tasks plus 3 bewusst blockierte Rückfragen
(offene Fragen aus Spec §11). Jede Task hat Abhängigkeiten, Spec-Verweise, Akzeptanzkriterien
und „Nicht im Scope“. Das Format ist maschinenlesbar. Die Aufteilung folgt der Regel aus der
alten `AGENTS.md`: Schema-Änderungen sind eigene Tasks, Fachlogik wird zuerst als testbare reine
Funktion gebaut (Elo, Satzregeln, Workflow) und erst danach mit DB und UI verdrahtet.

T001 (Grundgerüst) erledigt jetzt `scripts/bootstrap-web.sh` deterministisch. Beim Testen des
Skripts fielen zwei echte Probleme auf, die jetzt behoben sind:
1. `create-next-app` pinnt `@types/node@^20`, Vitest 5 verlangt ≥ 22, das führte zu einem
   npm-Abhängigkeitskonflikt.
2. Das Next-Template lädt Schriften beim **Build** von Google Fonts. Das ist ein Cloud-Zugriff und
   bricht offline bzw. in Docker. Es wurde durch System-Schriften ersetzt.

Danach: Typecheck, Lint, Test und Build grün.

## 6. Entfernt

- `langgraph/` (ersetzt durch `autopilot/`).
- Hybrid-Planner über eine Cloud-API: widerspricht dem Ziel „komplett lokal“. Technisch bleibt es
  möglich, da der Autopilot jeden OpenAI-kompatiblen Endpunkt ansprechen kann
  (`LLM_BASE_URL`).
- `phi4-mini`.

## 7. Nachweislich getestet

- OpenCode 1.18.33: Konfiguration lädt, alle Agenten werden erkannt, Rechte werden wie
  beabsichtigt aufgelöst; `opencode run` mit allow/deny/ask-Verhalten geprüft.
- `scripts/bootstrap-web.sh`: kompletter Lauf, `check.sh` grün (inkl. `next build`).
- Autopilot Ende-zu-Ende mit echtem OpenCode und simuliertem Modell:
  - Erfolgsfall mit einer Revision (Spec-FAIL → Coder erneut → PASS → Commit).
  - Fehlerfall: 3× FAIL → Rollback, Patch gesichert, Task `blocked`, Commit.
  - Ein Coder, der per Shell `AGENTS.md` manipuliert, wird zurückgesetzt.
- 19 Unit-Tests (TASKS-Parser, Abhängigkeiten ohne Zyklen, Verdict-Parser, Routing,
  Event-Parsing, Spec-Auszüge).

**Nicht getestet** (keine GPU in der Testumgebung): tatsächliche Geschwindigkeit und
Speicheraufteilung auf der RTX 4070 Ti, Qualität der Modellantworten, llama.cpp-Profil,
Tailscale.
