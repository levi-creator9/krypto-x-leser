"""
Krypto-X-Leser – läuft auf GitHub Actions (alle ~5 Minuten).
Öffnet die "Following"-Timeline des Bot-Accounts in einem unsichtbaren Browser,
liest die neuesten Posts und schickt sie an den Krypto-Monitor auf Supabase.
Dort werden sie wie alle anderen Meldungen gefiltert, von der KI bewertet und ggf. aufs Handy gepusht.

Benötigte GitHub-Secrets:
  X_AUTH_TOKEN    – Cookie "auth_token" des eingeloggten Bot-Accounts
  X_CT0           – Cookie "ct0" des eingeloggten Bot-Accounts
  MONITOR_URL     – https://<projekt>.supabase.co/functions/v1/monitor
  MONITOR_SECRET  – Geheimnis des Monitors
"""
import json
import os
import re
import sys
import time
import urllib.request

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

MAX_POSTS = 60
SCROLLS = 4


def post_text(article):
    teile = article.query_selector_all('[data-testid="tweetText"]')
    return "\n".join(t.inner_text().strip() for t in teile if t.inner_text().strip())


def lesen(auth_token: str, ct0: str):
    tweets = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            locale="en-US",
            viewport={"width": 1280, "height": 1800},
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
        )
        ctx.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/", "secure": True, "httpOnly": True},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/", "secure": True},
        ])
        page = ctx.new_page()
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)

        if "/login" in page.url or "/i/flow/login" in page.url:
            raise RuntimeError("Nicht eingeloggt – X_AUTH_TOKEN / X_CT0 abgelaufen oder falsch")

        # Chronologische "Following"-Timeline statt "For you"
        try:
            page.get_by_role("tab", name=re.compile("^Following$")).click(timeout=15000)
        except PWTimeout:
            print("Hinweis: 'Following'-Tab nicht gefunden – lese Standard-Timeline")

        try:
            page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)
        except PWTimeout:
            # Diagnose (ohne persönliche Daten): wo sind wir, was steht auf der Seite?
            try:
                sichtbar = page.inner_text("body")[:400].replace("\n", " | ")
            except Exception:
                sichtbar = "?"
            print("DIAGNOSE url:", page.url)
            print("DIAGNOSE titel:", page.title())
            print("DIAGNOSE text:", sichtbar)
            raise RuntimeError("Keine Posts sichtbar – evtl. gesperrt, Captcha oder noch niemandem gefolgt")

        for _ in range(SCROLLS):
            for a in page.query_selector_all('article[data-testid="tweet"]'):
                link_el = a.query_selector('a[href*="/status/"]:has(time)')
                if not link_el:
                    continue
                href = link_el.get_attribute("href") or ""
                m = re.match(r"^/([^/]+)/status/(\d+)", href)
                if not m:
                    continue
                autor, sid = m.group(1), m.group(2)
                if sid in tweets:
                    continue
                zeit_el = a.query_selector("time")
                text = post_text(a)
                if not text:
                    continue
                # Reposts: Hinweis mitschicken
                sozial = a.query_selector('[data-testid="socialContext"]')
                if sozial:
                    text = f"[{sozial.inner_text().strip()}] {text}"
                tweets[sid] = {
                    "id": sid,
                    "autor": autor,
                    "text": text,
                    "link": f"https://x.com/{autor}/status/{sid}",
                    "zeit": zeit_el.get_attribute("datetime") if zeit_el else None,
                }
            if len(tweets) >= MAX_POSTS:
                break
            page.mouse.wheel(0, 2500)
            time.sleep(2)
        browser.close()
    return list(tweets.values())[:MAX_POSTS]


def senden(url: str, secret: str, nutzlast: dict):
    req = urllib.request.Request(
        url.rstrip("/") + "?x=1",
        data=json.dumps(nutzlast).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-monitor-secret": secret},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def main():
    fehlend = [k for k in ("X_AUTH_TOKEN", "X_CT0", "MONITOR_URL", "MONITOR_SECRET") if not os.environ.get(k)]
    if fehlend:
        print("Noch nicht eingerichtet – fehlende Secrets:", ", ".join(fehlend))
        return  # still beenden, damit GitHub keine Fehler-Mails schickt
    url, secret = os.environ["MONITOR_URL"], os.environ["MONITOR_SECRET"]
    try:
        tweets = lesen(os.environ["X_AUTH_TOKEN"].strip(), os.environ["X_CT0"].strip())
        print(f"{len(tweets)} Posts gelesen")
        print(senden(url, secret, {"tweets": tweets}))
    except Exception as e:  # Fehler auch an den Monitor melden, damit er im Status sichtbar ist
        print("FEHLER:", e)
        try:
            senden(url, secret, {"tweets": [], "fehler": str(e)[:300]})
        except Exception as e2:
            print("Konnte Fehler nicht melden:", e2)
        sys.exit(1)


if __name__ == "__main__":
    main()
