# Krypto-X-Leser

Liest alle ~5 Minuten die **„Following“-Timeline** des Bot-X-Accounts und schickt neue Posts an den
Krypto-Monitor auf Supabase. Dort werden sie gefiltert, von der KI (Gemini) bewertet und bei Bedarf als Push aufs Handy geschickt.

Läuft komplett kostenlos auf GitHub Actions (öffentliches Repository). Login-Daten liegen nur als verschlüsselte **Secrets** vor – nie im Code.

## Einrichtung (Secrets)
Repository → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Inhalt |
|---|---|
| `X_AUTH_TOKEN` | Cookie `auth_token` des eingeloggten Bot-Accounts |
| `X_CT0` | Cookie `ct0` des eingeloggten Bot-Accounts |
| `MONITOR_URL` | `https://cohozvqovreauxldqtqd.supabase.co/functions/v1/monitor` |
| `MONITOR_SECRET` | Geheimnis des Monitors |

### Cookies holen (am Mac, Chrome)
1. In Chrome bei x.com mit dem **Bot-Account** einloggen.
2. `Alt + Cmd + I` → Tab **Application** → links **Cookies → https://x.com**.
3. Wert von `auth_token` und `ct0` kopieren und als Secrets eintragen.
4. Danach in diesem Chrome **nicht ausloggen** (Ausloggen macht die Cookies ungültig).

## Testen
**Actions → X-Leser → Run workflow**. Im Log steht z. B. `42 Posts gelesen` und die Antwort des Monitors.

## Hinweise
- X mag automatisches Mitlesen nicht. Deshalb: eigener Zweit-Account, nur lesen, nur alle 5 Minuten.
- Laufen die Cookies ab, erscheint im Log „Nicht eingeloggt“ → Cookies neu holen und Secrets ersetzen.
- `python test_leser.py` testet die Lese-Logik offline.
