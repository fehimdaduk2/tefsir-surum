#!/usr/bin/env python3
"""İndirme sayıları → yönetim paneli (her saat .github/workflows/sayim.yml). Sayılar herkese açık bir dosyaya
yazılmaz: GitHub'ın bu iş için imzaladığı kısa ömürlü kimlik belgesiyle (OIDC) projenin sayacına gönderilir; sayaç
belgeyi GitHub'ın anahtarlarıyla doğrular (yalnız bu depo, main dalı). Yöntem: güncelleme dosyaları (Guncelleme-*)
ayrı sayılır; tarayıcıların ve denetleyicilerin her dosyadan indirmesi, her sürümün en az indirilen dosyası kadar düşülür."""
import base64, datetime, gzip, json, os, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request

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


# ---- Google Play: the statistics Play Console writes every day as CSV files (UTF-16) into its Cloud Storage bucket,
# read with a service account invited to Play Console (read-only: bulk reports, app quality). The secrets:
# GOOGLE_PLAY_ANAHTAR (the service account's JSON key) and GOOGLE_PLAY_KOVA (gs://pubsite_prod_rev_…); without them, skipped.
PKG = "com.tefsirhadis.kutuphane"


def google_token(key, scopes):
    head = b64u(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    now = int(time.time())
    body = b64u(json.dumps({"iss": key["client_email"], "scope": " ".join(scopes), "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3000}).encode())
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
        f.write(key["private_key"]); kf = f.name
    try:
        sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", kf], input=(head + "." + body).encode(), capture_output=True, check=True).stdout
    finally:
        os.unlink(kf)
    data = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": head + "." + body + "." + b64u(sig)}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30) as r:
        return json.load(r)["access_token"]


def gcs_csv(tok, bucket, name):
    url = "https://storage.googleapis.com/storage/v1/b/%s/o/%s?alt=media" % (bucket, urllib.parse.quote(name, safe=""))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404: return []
        raise
    for enc in ("utf-16", "utf-8-sig"):
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    import csv, io
    return list(csv.DictReader(io.StringIO(text)))


def num(v):
    try: return float(str(v).replace(",", "") or 0)
    except ValueError: return 0.0


def play():
    raw, bucket = os.environ.get("GOOGLE_PLAY_ANAHTAR", "").strip(), os.environ.get("GOOGLE_PLAY_KOVA", "").strip()
    if not (raw and bucket):
        return None
    key = json.loads(raw); bucket = bucket.replace("gs://", "").strip("/").split("/")[0]
    tok = google_token(key, ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/playdeveloperreporting"])
    today = datetime.date.today(); months = [today.strftime("%Y%m"), (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y%m")]
    days, ulke = {}, {}
    for m in months:
        for r in gcs_csv(tok, bucket, "stats/installs/installs_%s_%s_overview.csv" % (PKG, m)):
            d = r.get("Date"); 
            if not d: continue
            days.setdefault(d, {}).update({"yukle": int(num(r.get("Daily User Installs"))), "kaldir": int(num(r.get("Daily User Uninstalls"))),
                "cyukle": int(num(r.get("Daily Device Installs"))), "ckaldir": int(num(r.get("Daily Device Uninstalls"))),
                "toplam": int(num(r.get("Total User Installs"))), "aktif": int(num(r.get("Active Device Installs")))})
        for r in gcs_csv(tok, bucket, "stats/ratings/ratings_%s_%s_overview.csv" % (PKG, m)):
            d = r.get("Date")
            if d: days.setdefault(d, {}).update({"puan": round(num(r.get("Daily Average Rating")), 2), "puant": round(num(r.get("Total Average Rating")), 2)})
        for r in gcs_csv(tok, bucket, "stats/installs/installs_%s_%s_country.csv" % (PKG, m)):
            d, cc = r.get("Date"), (r.get("Country") or "").upper()
            if d and len(cc) == 2:
                ulke[(d, cc)] = {"gun": d, "cc": cc, "yukle": int(num(r.get("Daily User Installs"))), "aktif": int(num(r.get("Active Device Installs")))}
    out = {"gun": [dict(gun=d, **v) for d, v in sorted(days.items())][-62:], "ulke": sorted(ulke.values(), key=lambda x: x["gun"])[-1500:], "vital": []}
    # Android vitals (the Play Developer Reporting API): the crash and ANR rates of the last weeks, where Google has enough users for them
    try:
        end = today - datetime.timedelta(days=2); start = end - datetime.timedelta(days=27)
        ymd = lambda x: {"year": x.year, "month": x.month, "day": x.day}
        vit = {}
        for metric_set, metrics in (("crashRateMetricSet", ["crashRate", "userPerceivedCrashRate", "distinctUsers"]), ("anrRateMetricSet", ["anrRate", "userPerceivedAnrRate"])):
            body = {"timelineSpec": {"aggregationPeriod": "DAILY", "startTime": dict(ymd(start), timeZone={"id": "America/Los_Angeles"}), "endTime": dict(ymd(end), timeZone={"id": "America/Los_Angeles"})}, "metrics": metrics}
            req = urllib.request.Request("https://playdeveloperreporting.googleapis.com/v1beta1/apps/%s/%s:query" % (PKG, metric_set), data=json.dumps(body).encode(),
                                         headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                for row in json.load(r).get("rows", []):
                    st = row["startTime"]; d = "%04d-%02d-%02d" % (st["year"], st["month"], st["day"])
                    for mv in row.get("metrics", []):
                        v = mv.get("decimalValue", {}).get("value")
                        if v is not None: vit.setdefault(d, {})[mv["metric"]] = float(v)
        out["vital"] = [{"gun": d, "cokme": v.get("crashRate"), "pcokme": v.get("userPerceivedCrashRate"), "anr": v.get("anrRate"), "panr": v.get("userPerceivedAnrRate"), "kisi": int(v.get("distinctUsers") or 0)} for d, v in sorted(vit.items())]
    except Exception as e:
        print("Android vitals alınamadı:", e)
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
    try:
        gp = play()
    except Exception as e:
        print("Google Play atlandı:", e); gp = None
    payload = {"github": data, "appstore": app, "play": gp} if (app or gp) else data
    if gp: print("Google Play:", len(gp["gun"]), "gün,", len(gp["ulke"]), "ülke satırı,", len(gp["vital"]), "vitals günü")
    # GitHub's signed identity token for this job
    t = get(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=tefsir-sayac", os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"])["value"]
    req = urllib.request.Request(SAYAC, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + t, "User-Agent": "tefsir-sayim"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(r.status, r.read().decode()[:200])


if __name__ == "__main__":
    main()
