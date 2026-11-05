#!/usr/bin/env python3
"""The download counts shown in the program («Hakkında») and on the page: indirme.json, from the GitHub releases.
Run every day by .github/workflows/indirme.yml (and by hand: python3 araclar/indirme.py).

Counted: the files people download to install (Kurulum.exe, the macOS and Linux packages, the APK). Not counted:
- the copies the program updates itself from (Guncelleme-*, from 4.78 on): an update is not a new user;
- the checks made when a version is published: until 4.77 each file was downloaded once to check it (twice for 4.61
  and 4.74, whose check was run again); from 4.78 on the check reads GitHub's checksum and downloads nothing.
Before 4.78 the program's own updates fetched the same files, so the counts up to then include some updates.
Google Play's installs are not in GitHub: araclar/play.json ({"yukleme": n, "tarih": "YYYY-MM-DD"}), written by
hand from the Play Console, is added when present."""
import json, os, re, urllib.request, datetime

API = "https://api.github.com/repos/fehimdaduk2/tefsir-surum/releases?per_page=100&page=%d"
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
EXTRA_CHECKS = {"v4.61": 1, "v4.74": 1}   # versions whose files were checked a second time


def kind(name):
    n = name.lower()
    if n.startswith("guncelleme-"): return None
    if n == "kurulum.exe": return "windows"
    if "macos" in n: return "mac"
    if "linux" in n: return "linux"
    if n.endswith(".apk"): return "android"
    return None


def upd_kind(name):
    return kind(name[len("Guncelleme-"):]) if name.lower().startswith("guncelleme-") else None


def ver(tag):
    m = re.match(r"v(\d+)\.(\d+)", tag)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def releases():
    out, page = [], 1
    while True:
        req = urllib.request.Request(API % page, headers={"Accept": "application/vnd.github+json", "User-Agent": "tefsir-indirme"})
        if os.environ.get("GITHUB_TOKEN"):
            req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.load(r)
        out += batch
        if len(batch) < 100: return out
        page += 1


def main():
    c = {"windows": 0, "mac": 0, "linux": 0, "android": 0}
    u = {"windows": 0, "mac": 0, "linux": 0, "android": 0}
    for r in releases():
        checks = (1 + EXTRA_CHECKS.get(r["tag_name"], 0)) if ver(r["tag_name"]) <= (4, 77) else 0
        for a in r["assets"]:
            k = kind(a["name"])
            if k: c[k] += max(0, a["download_count"] - checks)
            k = upd_kind(a["name"])
            if k: u[k] += a["download_count"]
    out = {"tarih": datetime.date.today().isoformat(), "indirme": c, "guncelleme": u}
    pf = os.path.join(HERE, "play.json")
    if os.path.exists(pf):
        out["play"] = json.load(open(pf, encoding="utf-8"))
    path = os.path.join(ROOT, "indirme.json")
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    if old and {k: v for k, v in old.items() if k != "tarih"} == {k: v for k, v in out.items() if k != "tarih"}:
        print("değişiklik yok"); return
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(path, "a").write("\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
