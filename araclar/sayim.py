#!/usr/bin/env python3
"""İndirme sayıları → yönetim paneli (her saat .github/workflows/sayim.yml). Sayılar herkese açık bir dosyaya
yazılmaz: GitHub'ın bu iş için imzaladığı kısa ömürlü kimlik belgesiyle (OIDC) projenin sayacına gönderilir; sayaç
belgeyi GitHub'ın anahtarlarıyla doğrular (yalnız bu depo, main dalı). Yöntem: güncelleme dosyaları (Guncelleme-*)
ayrı sayılır; tarayıcıların ve denetleyicilerin her dosyadan indirmesi, her sürümün en az indirilen dosyası kadar düşülür."""
import json, os, urllib.request

API = "https://api.github.com/repos/fehimdaduk2/tefsir-surum/releases?per_page=100&page=%d"
SAYAC = "https://tefsir-sayac.tefsirkutuphanesi.workers.dev/indirme"


def kind(n):
    n = n.lower()
    if n.startswith("guncelleme-"): return None
    if n == "kurulum.exe": return "windows"
    if "macos" in n: return "mac"
    if "linux" in n: return "linux"
    if n.endswith(".apk"): return "android"
    return None


def get(url, tok=None):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "tefsir-sayim"})
    if tok: req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    rels, page = [], 1
    while True:
        b = get(API % page, os.environ.get("GITHUB_TOKEN")); rels += b
        if len(b) < 100: break
        page += 1
    rows = {}
    for r in rels:
        main_ = [(kind(a["name"]), a["download_count"]) for a in r["assets"] if kind(a["name"])]
        floor = min((n for _, n in main_), default=0)
        for k, n in main_:
            rows[(k, r["tag_name"])] = rows.get((k, r["tag_name"]), 0) + n - floor
        for a in r["assets"]:
            if a["name"].lower().startswith("guncelleme-"):
                k = kind(a["name"][len("Guncelleme-"):])
                if k: rows[("g-" + k, r["tag_name"])] = rows.get(("g-" + k, r["tag_name"]), 0) + a["download_count"]
    data = [{"tur": k, "surum": v, "sayi": n} for (k, v), n in rows.items()]
    # GitHub's signed identity token for this job
    t = get(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=tefsir-sayac", os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"])["value"]
    req = urllib.request.Request(SAYAC, data=json.dumps(data).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + t, "User-Agent": "tefsir-sayim"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(r.status, r.read().decode()[:200])


if __name__ == "__main__":
    main()
