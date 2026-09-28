# PROJECT_SPEC.md – Badminton Inhouse-Liga

> Diese Datei ist die fachliche „Source of Truth" für den Planner-Agenten.
> Bei Widersprüchen zwischen Annahmen eines Agenten und diesem Dokument
> gewinnt immer dieses Dokument. Offene Punkte stehen explizit unter
> Abschnitt 11 „Offene Fragen" statt stillschweigend angenommen zu werden.
> Den verbindlichen Tech-Stack und die Repo-Struktur beschreibt `AGENTS.md`.

---

## 1. Ziel & Zielgruppe

Interne Web-App für eine geschlossene Badminton-Gruppe (kein öffentlicher
Betrieb, kein Publikumsverkehr). Zweck:

- Ergebnisse von Matches schnell und ohne Reibung direkt auf dem Platz/in
  der Halle erfassen (Smartphone, während/kurz nach dem Spiel).
- Automatische, faire Bewertung der Spielstärke über ein Rating-System,
  getrennt für Einzel und Doppel.
- Nachvollziehbare Ligatabelle über die Zeit.
- Optional: Video-Zuordnung zu Matches (z. B. Handy-Mitschnitt hochgeladen
  auf YouTube/Drive, hier nur verlinkt).

Zielgruppe: feste, bekannte Personengruppe (Verein/Freundeskreis/Firma).
Kein Self-Signup für Fremde – Zugang nur über Einladung/Admin-Freischaltung,
und **kein öffentlicher Internet-Zugriff** (siehe Abschnitt 4).

---

## 2. Nutzerrollen

| Rolle          | Rechte |
|----------------|--------|
| **Spieler**    | Eigenes Profil bearbeiten, Matches anlegen/bearbeiten (Draft), an denen er/sie beteiligt ist, Publish anstoßen, Matches der Gegenseite bestätigen (Vier-Augen-Prinzip, siehe 3.3), Ligatabelle einsehen |
| **Admin**      | Alles was Spieler dürfen + Nutzer einladen/verwalten, jedes Match bearbeiten/löschen/re-publishen, Bestätigung im Namen der Gegenseite übersteuern (z. B. wenn Gegner nicht reagiert), Rating manuell korrigieren (mit Pflicht-Begründung, siehe Audit-Log), Saison eröffnen/schließen |
| **Zuschauer** *(optional, siehe offene Fragen)* | Nur Lesezugriff auf Ligatabelle und published Matches, kein Login nötig oder separater Read-only-Account |

Ein Match hat immer zwei **Teams** (Team A / Team B):
- **Einzel:** je 1 Spieler pro Team.
- **Doppel:** je 2 Spieler pro Team.

Jeder beteiligte Spieler (beide Teams) darf ein Draft-Match bearbeiten –
das verhindert Blockaden, wenn eine Person das Handy weglegt.

---

## 3. Kernfunktionen

### 3.1 Auth & Profile
- Einladungsbasierte Registrierung (Admin erstellt Einladungslink oder legt
  Account direkt an, Spieler setzt beim ersten Login ein Passwort).
- Login (E-Mail/Benutzername + Passwort). Passwort-Reset per E-Mail.
- Spielerprofil: Anzeigename, optionales Profilfoto, **zwei** aktuelle
  Ratings (Einzel, Doppel), Rating-Verlauf je Kategorie (Graph), Bilanz
  (Siege/Niederlagen je Kategorie), Match-Historie.

### 3.2 Schnelle Match-Erfassung ("Quick Add") – zentrales Feature
Das ist der wichtigste Flow der ganzen App und muss auf dem Handy in
möglichst wenigen Taps durchführbar sein:

1. Button „Neues Match" (groß, auf der Startseite prominent erreichbar,
   auch als PWA-Shortcut/Homescreen-Icon-Aktion vorgesehen).
2. Modus wählen: **Einzel** oder **Doppel** (Default: zuletzt genutzter Modus).
3. Spieler auswählen: bei Einzel 2 Spieler (Team A / Team B), bei Doppel
   4 Spieler (2 pro Team) – Suchfeld mit Autocomplete; zuletzt/häufig
   gespielte Gegner/Partner werden oben vorgeschlagen.
4. Ergebnis eintragen: mindestens Sieger, im Idealfall Satzstände
   (Badminton: Best-of-3-Sätze, jeweils bis 21 Punkte, ab 20:20
   Verlängerung bis Zwei-Punkte-Vorsprung, Cap bei 30). UI soll das über
   einfache Zahleneingabe/Stepper pro Satz lösen, nicht über Freitext.
5. Speichern → Match wird **sofort als Draft angelegt**, kein Zwischenschritt,
   keine Pflichtfelder außer „Teams + mindestens ein Satzergebnis".
6. Datum/Uhrzeit wird automatisch auf „jetzt" gesetzt, kann später korrigiert
   werden.

### 3.3 Match-Status-Workflow (mit Vier-Augen-Prinzip)

```
[Draft] --(bearbeiten: Sätze, Datum, Ort, Video-URL, Notizen)--> [Draft]
[Draft] --(Publish anfragen, durch ein Mitglied von Team A oder B)--> [Pending Confirmation]
[Pending Confirmation] --(Bestätigung durch ein Mitglied der JEWEILS ANDEREN Seite)--> [Published]
                                                                     → triggert Rating-Berechnung
[Pending Confirmation] --(Ablehnung durch die andere Seite, z. B. falsches Ergebnis)--> [Draft]
[Published] --(Admin: Reopen/Korrektur)--> [Draft] → erneutes Anfragen+Bestätigen nötig
```

- **Draft:** frei editierbar durch alle beteiligten Spieler und Admin.
  Fließt NICHT in Rating oder Ligatabelle ein.
- **Publish anfragen:** jede beteiligte Person kann diesen Schritt auslösen.
  Das Match wechselt in „Pending Confirmation" und ist ab jetzt nur noch
  lesbar für die anfragende Seite (Änderungen erst nach Ablehnung wieder
  möglich, damit sich niemand nach dem Bestätigungs-Request das Ergebnis
  „zurechtbiegt").
- **Bestätigen:** muss von jemandem aus der **anderen** Seite kommen als
  der, die/der die Anfrage gestellt hat (also nicht Selbstbestätigung).
  Bei Doppel reicht die Bestätigung durch eine der beiden Personen der
  Gegenseite.
- **Ablehnen:** setzt das Match zurück auf Draft, mit optionalem
  Kommentarfeld ("falscher Satzstand" etc.), damit es korrigiert werden kann.
- **Admin-Override:** falls die Gegenseite nicht reagiert (z. B. inaktiv),
  kann ein Admin die Bestätigung im Audit-Log nachvollziehbar übersteuern.
- **Publish** (technisch: erfolgreiche Bestätigung) berechnet danach
  automatisch:
  - Rating-Änderung für alle beteiligten Spieler, in der jeweils
    passenden Kategorie (Einzel- oder Doppel-Rating)
  - Aktualisierung der Ligatabelle(n)
  - Eintrag in die Rating-Historie aller beteiligten Spieler
- **Korrektur nach Publish:** nur durch Admin, über „Reopen". Das setzt das
  Match zurück auf Draft, macht die zugehörige Rating-Änderung rückgängig
  (Rating-Historie wird nicht gelöscht, sondern als „reverted" markiert –
  Nachvollziehbarkeit geht vor Löschen). Der volle Anfrage+Bestätigen-Zyklus
  muss danach erneut durchlaufen werden.

### 3.4 Video-Zuordnung
- Freies URL-Feld pro Match (optional, kann auch nachträglich in einem
  bereits published Match ergänzt werden, ohne Rating neu zu triggern).
- Unterstützte Embed-Quellen: YouTube, generische `<iframe>`-fähige Links.
  Bei nicht erkanntem Format: einfacher externer Link statt Embed-Versuch.
- Mehrere Videos pro Match möglich (z. B. zwei Kamerawinkel) – Liste statt
  Einzelfeld.

### 3.5 Rating-System (ELO-basiert, getrennt für Einzel & Doppel)
- Klassischer Elo-Algorithmus, Startwert für neue Spieler: **1000**
  (separat für Einzel-Rating und Doppel-Rating – ein guter Einzelspieler
  ist nicht automatisch ein gutes Doppel-Paar-Mitglied).
- K-Faktor gestaffelt je Kategorie (wie im Schach üblich, verhindert, dass
  etablierte Ratings durch einzelne Ausreißer zu stark schwanken):
  - Erste 10 gewertete Matches eines Spielers **in der jeweiligen
    Kategorie**: K = 40
  - Danach: K = 20
- Berechnung erfolgt rein auf Basis von Sieg/Niederlage des Matches
  (nicht satzgewichtet) – einfach, transparent, nachvollziehbar.
- **Doppel-Berechnung (vereinfachtes Team-Elo):** die erwartete
  Gewinnwahrscheinlichkeit wird auf Basis des **Durchschnitts-Ratings**
  beider Team-Mitglieder berechnet (Team-Rating = Mittelwert). Die
  resultierende Rating-Änderung wird beiden Spielern eines Teams
  **identisch** gutgeschrieben/abgezogen. Das ist eine bewusste
  Vereinfachung (kein individuelles Beitrags-Tracking pro Ballwechsel) –
  ausreichend für eine interne Freizeitliga.
- Bei Publish werden alle beteiligten Spieler-Ratings der jeweiligen
  Kategorie gleichzeitig aktualisiert, Berechnung als reine, gut testbare
  Funktion isoliert vom Rest der App (leicht unit-testbar, keine
  Seiteneffekte außer Rückgabewert).
- Rating-Historie: jede Rating-Änderung wird als eigener Datensatz
  gespeichert (Zeitpunkt, Kategorie, altes Rating, neues Rating,
  zugehöriges Match).

### 3.6 Ligatabelle / Standings
- **Zwei getrennte Tabellen:** Einzel-Rangliste und Doppel-Rangliste
  (ein Spieler taucht in beiden auf, mit jeweils eigenem Rating).
- Sortiert nach aktuellem Rating (absteigend).
- Spalten: Platzierung, Name, Rating, Anzahl Matches, Siege/Niederlagen,
  Siegquote, Trend (Rating-Änderung der letzten N Matches, z. B. Pfeil
  hoch/runter).
- Filterbar nach Zeitraum/Saison (siehe 3.8).

### 3.7 Match-Historie & Head-to-Head
- Liste aller published Matches eines Spielers, neueste zuerst, mit Filter
  nach Einzel/Doppel.
- Head-to-Head-Ansicht zwischen zwei ausgewählten Spielern (Bilanz,
  Satzverhältnis, letzte Begegnungen) – bezieht sich auf Einzel-Matches;
  bei Doppel wird stattdessen eine Paarungs-Historie (welches Duo hat wie
  oft gegen welches Duo gespielt) angezeigt.

### 3.8 Saisons *(siehe offene Fragen zu Details)*
- Grundidee: Ligatabelle kann optional nach Saison gefiltert werden, Rating
  selbst läuft aber kontinuierlich weiter (kein harter Reset), sodass die
  Historie nicht verloren geht. Admin kann Saison-Zeiträume anlegen
  (Start-/Enddatum, Name z. B. „Sommer 2027").

### 3.9 Admin-Funktionen
- Nutzer einladen/deaktivieren (kein hartes Löschen – deaktivierte Spieler
  bleiben in der Historie sichtbar, tauchen aber nicht mehr als aktiv in
  der Tabelle auf, falls gewünscht).
- Match reopen/korrigieren/löschen, Bestätigung übersteuern.
- Manuelle Rating-Korrektur nur mit Pflichtfeld „Begründung", landet im
  Audit-Log.
- Saison-Verwaltung.

### 3.10 Audit-Log
- Protokolliert: wer hat wann welches Match angelegt/geändert/Publish
  angefragt/bestätigt/abgelehnt/reopened, wer hat manuell ein Rating
  korrigiert und warum, wer hat eine Bestätigung als Admin übersteuert.
- Nur für Admins einsehbar. Dient Nachvollziehbarkeit, nicht Moderation.

---

## 4. Mobile & Hosting-Anforderungen

- **Mobile-first UI**, primär für die Nutzung während/direkt nach dem
  Spielen auf dem Smartphone gedacht. Desktop-Ansicht ist sekundär, aber
  für Admin-Aufgaben und die Ligatabelle am Bildschirm sinnvoll.
- **PWA (Progressive Web App):** installierbar auf dem Homescreen, damit
  „Neues Match" mit einem Tap ohne Browser-Umweg erreichbar ist. Kein
  natives iOS/Android-App-Store-Release geplant (unnötiger Aufwand für
  eine interne App).
- **Selbst hostbar:** Backend + Frontend + Datenbank über Docker Compose
  auf einem Server im lokalen Netz oder einem kleinen VPS.
- **Zugriff unterwegs: ausschließlich über Tailscale/VPN, kein öffentlicher
  Internet-Zugang.** Konsequenzen für Setup und Tasks:
  - Der Server (bzw. der Docker-Host) muss dem Tailscale-Netz (Tailnet)
    beitreten; die App wird NICHT über eine öffentliche Domain mit
    Portweiterleitung exponiert.
  - Jedes Gerät, das unterwegs zugreifen soll (Spieler-Smartphones), braucht
    die Tailscale-App und muss demselben Tailnet beitreten (einmaliger
    Einrichtungsaufwand pro Person/Gerät – das ist eine bewusste
    Sicherheits-Komfort-Abwägung, siehe Out-of-Scope-Hinweis unten).
  - HTTPS/Zertifikate können optional über Tailscale's eigene TLS-Zertifikate
    (MagicDNS + HTTPS-Feature) laufen, statt über einen klassischen Reverse
    Proxy mit Let's-Encrypt – das spart eine öffentlich erreichbare
    Angriffsfläche komplett.
  - Diese Entscheidung reduziert die Registrierungs-/Login-Sicherheitsanforderungen
    etwas (kein Angriff durch beliebige Internet-Bots), ersetzt aber nicht
    die Notwendigkeit von Passwort-Hashing etc. (siehe Abschnitt 6) – falls
    später doch öffentlicher Zugriff gewünscht wird, sollen keine
    Kernannahmen der App davon abhängen.

---

## 5. Datenmodell (grob, für Drizzle/PostgreSQL)

> **Hinweis (Setup-Überarbeitung 09/2026):** Auth läuft über Better Auth. Die Tabelle
> `players` wird als Better-Auth-Tabelle `user` umgesetzt (mit den unten genannten
> Zusatzfeldern); das Passwort-Hash liegt dort in der Better-Auth-Tabelle `account`
> statt in `players.password_hash`. `is_admin` wird als `role` ("player" | "admin")
> abgebildet. Fachlich ändert sich nichts. Zusätzlich gibt es eine Tabelle `invitations`
> für den Einladungsflow (siehe TASKS.md T012).

### `players`
| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| display_name | text | |
| email | text | unique, für Login |
| password_hash | text | |
| avatar_url | text | optional |
| current_rating_singles | integer | denormalisiert für schnelle Sortierung, Quelle der Wahrheit bleibt `rating_history` |
| current_rating_doubles | integer | s.o., getrennt von Einzel |
| is_admin | boolean | |
| is_active | boolean | deaktivierte Spieler bleiben historisch sichtbar |
| created_at | timestamp | |

### `matches`
| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| match_type | enum | `singles` \| `doubles` |
| status | enum | `draft` \| `pending_confirmation` \| `published` |
| played_at | timestamp | vom Nutzer editierbar, Default = Erstellzeitpunkt |
| location | text | optional |
| notes | text | optional |
| created_by | uuid | FK players |
| publish_requested_by | uuid | nullable, FK players |
| publish_requested_at | timestamp | nullable |
| confirmed_by | uuid | nullable, FK players (wer die Bestätigung ausgelöst hat, ggf. ein Admin bei Override) |
| confirmed_at | timestamp | nullable |
| published_at | timestamp | nullable |
| created_at / updated_at | timestamp | |

### `match_participants`
Ersetzt feste `player_a_id`/`player_b_id`-Spalten, damit Einzel (2 Zeilen)
und Doppel (4 Zeilen) mit derselben Struktur abgebildet werden.

| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| match_id | uuid | FK matches |
| player_id | uuid | FK players |
| team | enum | `A` \| `B` |

### `match_sets`
| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| match_id | uuid | FK matches |
| set_number | integer | 1–3 |
| team_a_points | integer | |
| team_b_points | integer | |

### `match_videos`
| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| match_id | uuid | FK matches |
| url | text | |
| label | text | optional, z. B. "Kamera 1" |

### `rating_history`
| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| player_id | uuid | FK players |
| rating_type | enum | `singles` \| `doubles` |
| match_id | uuid | nullable (nullable für manuelle Admin-Korrekturen) |
| rating_before | integer | |
| rating_after | integer | |
| reason | text | Pflicht bei manueller Korrektur, sonst z. B. "match_published" |
| reverted | boolean | true, wenn zugehöriges Match reopened wurde |
| created_at | timestamp | |

### `seasons`
| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| name | text | z. B. "Sommer 2027" |
| starts_at / ends_at | timestamp | |

### `audit_log`
| Feld | Typ | Hinweis |
|---|---|---|
| id | uuid | PK |
| actor_id | uuid | FK players |
| action | text | z. B. "match.publish_requested", "match.confirmed", "match.confirmation_overridden", "rating.manual_correction" |
| target_type / target_id | text / uuid | |
| details | jsonb | |
| created_at | timestamp | |

---

## 6. Nicht-funktionale Anforderungen

- **Last:** kleine Nutzerzahl (geschlossene Gruppe), keine besonderen
  Performance-Anforderungen. Trotzdem: Quick-Add-Flow muss auch bei
  schlechter Hallen-Mobilfunkverbindung robust funktionieren (optimistisches
  UI-Update, Fehlertoleranz bei kurzzeitig fehlender Verbindung).
- **Sicherheit:** kein öffentlicher Signup, Passwort-Hashing (scrypt als Better-Auth-Standard, alternativ argon2/bcrypt),
  Rate-Limiting auf Login. Kein öffentlicher Internet-Zugang (siehe
  Abschnitt 4) – Zugriff nur innerhalb des Tailnet.
- **Datenschutz:** Profilfotos und Namen sind personenbezogene Daten –
  auch bei „nur intern" gilt: nur für eingeladene Nutzer sichtbar, kein
  Search-Engine-Indexing (robots.txt / noindex), keine Weitergabe an Dritte.
- **Backups:** regelmäßiges automatisiertes Datenbank-Backup (z. B. täglich,
  Aufbewahrung konfigurierbar).
- **Browser-Support:** aktuelle mobile Safari (iOS) und Chrome (Android)
  als Priorität 1, Desktop-Chrome/Firefox als Priorität 2.
- **Sprache:** UI auf Deutsch.

---

## 7. Design-Vorgaben

- Mobile-first, große Touch-Ziele (Finger auf dem Feld, evtl. verschwitzte
  Hände – keine winzigen Buttons).
- Der „Neues Match"-Flow soll mit möglichst wenigen Taps auskommen; jeder
  zusätzliche Pflicht-Screen im Quick-Add-Flow braucht eine explizite
  Begründung, warum er nötig ist. Die Bestätigungs-Anfrage nach „Publish
  anfragen" soll für die Gegenseite ebenfalls mit einem Tap erledigt sein
  (z. B. Push-/In-App-Hinweis „Match X wartet auf deine Bestätigung").
- Klare visuelle Unterscheidung zwischen Draft-, Pending-Confirmation- und
  Published-Matches (z. B. Farbe/Badge), damit niemand ein unbestätigtes
  Ergebnis mit einem finalen verwechselt.
- Farbschema/Branding: siehe offene Fragen.

---

## 8. Beispiel User Stories

- Als Spieler will ich nach einem Match in möglichst wenigen Taps das
  Ergebnis eintragen können, damit ich das Handy schnell wieder weglegen
  und weiterspielen kann.
- Als Spieler will ich ein Draft-Match noch nachträglich korrigieren können
  (z. B. falscher Satzstand), bevor ich die Bestätigung anfrage.
- Als Spieler will ich benachrichtigt werden, wenn ein Match auf meine
  Bestätigung wartet, damit ich zeitnah reagieren kann.
- Als Spieler will ich ein fälschlich angefragtes Ergebnis ablehnen können,
  damit keine falschen Zahlen in mein Rating einfließen.
- Als Spieler will ich sehen, wie sich mein Einzel- und Doppel-Rating
  getrennt über die Zeit entwickelt haben.
- Als Admin will ich ein fehlerhaft published Match zurückziehen können,
  ohne dass die Historie verloren geht.
- Als Spieler will ich die Bilanz gegen einen bestimmten Gegner (Einzel)
  bzw. gegen ein bestimmtes Duo (Doppel) einsehen können.

---

## 9. Out of Scope (bewusst NICHT Teil dieses Projekts)

- Öffentliche Registrierung / Self-Signup ohne Einladung.
- Öffentlicher Internet-Zugang ohne VPN (bewusste Entscheidung, siehe
  Abschnitt 4 – falls sich das später ändert, ist das eine explizite
  Spec-Änderung, keine stillschweigende Erweiterung).
- Turnierbaum-/Bracket-Generierung (reine Liga, kein K.-o.-Turniermodus).
- Individuelles Beitrags-Tracking pro Spieler innerhalb eines Doppel-Matches
  (z. B. wer hat mehr Punkte gemacht) – Doppel-Rating wird bewusst
  vereinfacht pro Team berechnet (siehe 3.5).
- Zahlungs-/Abrechnungsfunktionen (z. B. Hallenmiete-Splitting).
- Natives Mobile-App-Store-Release (iOS/Android) – PWA reicht.
- Mehrsprachigkeit (nur Deutsch, kein i18n-Layer in v1).

---

## 10. Definition of Done (pro Feature)

Eine Task gilt erst als abgeschlossen, wenn:
1. Spec-Reviewer bestätigt: Funktionalität entspricht exakt der Anforderung.
2. Quality-Reviewer bestätigt: Code-Qualität/Struktur/Fehlerbehandlung ok.
3. Für Kernlogik (Rating-Berechnung Einzel & Doppel, Publish/Confirm-Workflow)
   existiert mindestens ein automatisierter Test.
4. Die Funktion ist auf einer mobilen Viewport-Breite (~375px) manuell/optisch
   geprüft, nicht nur am Desktop-Breakpoint entwickelt. (Diesen Punkt kann der
   Autopilot nicht prüfen – er bleibt beim Menschen, siehe README „Nach dem Lauf".)

---

## 11. Offene Fragen

*(vom Menschen zu klären, bevor der Planner die entsprechenden Tasks final
zuschneidet)*

- Soll es Saison-Resets geben (Rating setzt sich pro Saison zurück) oder
  bleibt das Rating durchgängig, wie aktuell in der Spec angenommen?
- Zuschauer-/Read-only-Rolle gewünscht, oder ist der Zugang ausschließlich
  für aktive Spieler gedacht?
- Soll es Benachrichtigungen geben (z. B. „Match wartet auf deine
  Bestätigung", „Dein Rating hat sich geändert") per E-Mail/Push, oder
  reicht ein reiner In-App-Hinweis beim nächsten Öffnen?
- Doppel-Partner-Wechsel: soll es eine Ansicht geben, die zeigt, mit
  welchem Partner ein Spieler am erfolgreichsten war (reine Statistik,
  kein Einfluss auf Rating-Berechnung)?
