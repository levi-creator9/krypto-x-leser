"""Test der Lese-Logik an einer nachgebauten X-Seite (ohne Internet). python test_leser.py"""
import re
import sys

from playwright.sync_api import sync_playwright

import leser

SEITE = """<html><body>
<div role="tablist"><div role="tab">For you</div><div role="tab" onclick="this.dataset.k=1">Following</div></div>
<article data-testid="tweet">
  <a href="/realDonaldTrump/status/111"><time datetime="2026-11-25T01:30:00.000Z">1m</time></a>
  <div data-testid="tweetText">Hyperliquid is doing an <b>incredible</b> job!</div>
</article>
<article data-testid="tweet">
  <div data-testid="socialContext">WatcherGuru reposted</div>
  <a href="/tier10k/status/222"><time datetime="2026-11-25T01:31:00.000Z">2m</time></a>
  <div data-testid="tweetText">JUST IN: Fed cuts rates</div><div data-testid="tweetText">by 25bps</div>
</article>
<article data-testid="tweet"><a href="/foo/status/333"><time datetime="x">3m</time></a></article>
<article data-testid="tweet"><a href="/foo/photo/1">bild</a><div data-testid="tweetText">ohne Link</div></article>
</body></html>"""

fehler = []


def check(n, b, info=""):
    print(("  ✅ " if b else "  ❌ ") + n + ("" if b else f"  {info}"))
    if not b:
        fehler.append(n)


# goto/Login umgehen: Seite direkt setzen
orig = leser.sync_playwright


class FakePW:
    def __enter__(self):
        self.p = orig().__enter__()
        real_launch = self.p.chromium.launch

        def launch(**kw):
            b = real_launch(**kw)
            real_ctx = b.new_context

            def new_context(**kw2):
                c = real_ctx(**kw2)
                real_page = c.new_page

                def new_page():
                    pg = real_page()
                    pg.goto = lambda *a, **k: pg.set_content(SEITE)
                    return pg
                c.new_page = new_page
                return c
            b.new_context = new_context
            return b
        self.p.chromium.launch = launch
        return self.p

    def __exit__(self, *a):
        return self.p.__exit__(*a) if hasattr(self.p, "__exit__") else None


leser.sync_playwright = lambda: FakePW()
leser.SCROLLS = 1
leser.time.sleep = lambda s: None

t = leser.lesen("x", "y")
ids = [x["id"] for x in t]
check("2 echte Posts gelesen", ids == ["111", "222"], ids)
check("Autor + Link", t[0]["autor"] == "realDonaldTrump" and t[0]["link"] == "https://x.com/realDonaldTrump/status/111", t[0])
check("Text vollständig", "incredible" in t[0]["text"], t[0]["text"])
check("Mehrteiliger Text + Repost-Hinweis", t[1]["text"].startswith("[WatcherGuru reposted]") and "25bps" in t[1]["text"], t[1]["text"])
check("Zeit übernommen", t[0]["zeit"] == "2026-11-25T01:30:00.000Z", t[0]["zeit"])
print("🎉 ALLE TESTS BESTANDEN" if not fehler else f"❌ {len(fehler)} FEHLER")
sys.exit(1 if fehler else 0)
