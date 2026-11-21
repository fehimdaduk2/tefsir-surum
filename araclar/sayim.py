#!/usr/bin/env python3
"""İndirme sayıları → yönetim paneli (her saat .github/workflows/sayim.yml). Sayılar herkese açık bir dosyaya
yazılmaz: GitHub'ın bu iş için imzaladığı kısa ömürlü kimlik belgesiyle (OIDC) projenin sayacına gönderilir; sayaç
belgeyi GitHub'ın anahtarlarıyla doğrular (yalnız bu depo, main dalı). Yöntem: güncelleme dosyaları (Guncelleme-*)
ayrı sayılır; tarayıcıların ve denetleyicilerin her dosyadan indirmesi, her sürümün en az indirilen dosyası kadar düşülür."""
import base64, datetime, gzip, json, os, subprocess, tempfile, time, urllib.error, urllib.request

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


# ---- the App Store: Apple's daily sales reports (App Store Connect API, the key the iOS build uses). Only the first
# downloads of the app are counted (product types 1, 1F, 1T); updates (7…) are not. Needs the vendor number
# (App Store Connect › Payments and Financial Reports, top left) as the APPLE_VENDOR_NUMBER secret; without it, skipped.
APP_ID = "6837263950"


def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def apple_jwt(kid, iss, p8):
    head = b64u(json.dumps({"alg": "ES256", "kid": kid, "typ": "JWT"}).encode())
    now = int(time.time())
    body = b64u(json.dumps({"iss": iss, "iat": now, "exp": now + 900, "aud": "appstoreconnect-v1"}).encode())
    with tempfile.NamedTemporaryFile("w", suffix=".p8", delete=False) as f:
        f.write(p8); key = f.name
    try:
        der = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key], input=(head + "." + body).encode(), capture_output=True, check=True).stdout
    finally:
        os.unlink(key)
    # DER (SEQUENCE of two INTEGERs) → the raw 64-byte r||s a JWT wants
    i = 2 + (der[1] & 0x7f if der[1] & 0x80 else 0)
    def integer(i):
        n = der[i + 1]; v = der[i + 2:i + 2 + n]; return v.lstrip(b"\0").rjust(32, b"\0"), i + 2 + n
    r, i = integer(i); s_, _ = integer(i)
    return head + "." + body + "." + b64u(r + s_)


def appstore():
    kid, iss, p8, vendor = (os.environ.get(k, "").strip() for k in ("APPLE_API_KEY_ID", "APPLE_API_ISSUER_ID", "APPLE_API_KEY_P8", "APPLE_VENDOR_NUMBER"))
    if not (kid and iss and p8 and vendor):
        return []
    tok, out = apple_jwt(kid, iss, p8), []
    for back in range(1, 6):
        d = (datetime.date.today() - datetime.timedelta(days=back)).isoformat()
        url = ("https://api.appstoreconnect.apple.com/v1/salesReports?filter[frequency]=DAILY&filter[reportDate]=%s"
               "&filter[reportSubType]=SUMMARY&filter[reportType]=SALES&filter[vendorNumber]=%s&filter[version]=1_1") % (d, vendor)
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok, "Accept": "application/a-gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                rows = gzip.decompress(r.read()).decode("utf-8").splitlines()
        except urllib.error.HTTPError as e:
            if e.code == 404:          # no report for that day (yet, or nothing sold)
                continue
            print("App Store raporu alınamadı:", d, e.code); continue
        head = rows[0].split("\t"); ix = {h: n for n, h in enumerate(head)}
        n = 0
        for line in rows[1:]:
            c = line.split("\t")
            if len(c) == len(head) and c[ix["Apple Identifier"]] == APP_ID and c[ix["Product Type Identifier"]].startswith("1"):
                n += int(float(c[ix["Units"]] or 0))
        out.append({"gun": d, "sayi": n})
    return out


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
    try:
        app = appstore()
    except Exception as e:      # the GitHub counts go on even if Apple does not answer
        print("App Store atlandı:", e); app = []
    payload = {"github": data, "appstore": app} if app else data
    # GitHub's signed identity token for this job
    t = get(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=tefsir-sayac", os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"])["value"]
    req = urllib.request.Request(SAYAC, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + t, "User-Agent": "tefsir-sayim"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(r.status, r.read().decode()[:200])


if __name__ == "__main__":
    main()
