#!/usr/bin/env python3
"""Microsoft Store (Partner Center) arayüzü: Store gönderim arayüzü ve Store istatistik arayüzü, Partner Center'a
eklenen «tefsir-yayin» Entra uygulamasıyla (rolleri: Developer, Marketer). Anahtarlar GitHub'daki secret'lardan gelir:
MSSTORE_TENANT, MSSTORE_CLIENT, MSSTORE_SECRET. Yalnız Python'un kendi kütüphaneleri.

  api.py dene                              bağlantıyı, uygulamayı ve bekleyen gönderimi gösterir
  api.py gonder <msix> <notlar.json>       yeni sürüm: paketi yükler, eski paketi kaldırır, «What's new»u yazar, incelemeye gönderir
  api.py istatistik <çıktı.json>           son 30 günün edinmeleri, kurulumları, puanları ve yorumları
"""
import io, json, os, sys, time, urllib.error, urllib.parse, urllib.request, zipfile, datetime as dt

APP = "9PKNVQC8GR2L"
API = "https://manage.devcenter.microsoft.com/v1.0/my"


def token():
    t, c, s = (os.environ.get(k, "") for k in ("MSSTORE_TENANT", "MSSTORE_CLIENT", "MSSTORE_SECRET"))
    if not (t and c and s):
        sys.exit("MSSTORE_TENANT / MSSTORE_CLIENT / MSSTORE_SECRET eksik (tefsir-surum › Settings › Secrets › Actions)")
    data = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": c, "client_secret": s,
                                   "resource": "https://manage.devcenter.microsoft.com"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request("https://login.microsoftonline.com/%s/oauth2/token" % t, data=data), timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        b = e.read().decode(errors="replace")
        try: b = json.loads(b).get("error_description", b).split("\n")[0]
        except Exception: pass
        sys.exit("Giriş olmadı (%d): %s" % (e.code, b[:300]))


def call(tok, method, path, body=None, ok404=False):
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            t = r.read(); return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        if ok404 and e.code == 404:
            return None
        b = e.read().decode(errors="replace")
        sys.exit("Store: %s %s → %d %s" % (method, url.replace(API, ""), e.code, b[:600]))


def dene():
    tok = token(); print("giriş tamam")
    a = call(tok, "GET", "/applications/%s" % APP)
    print("uygulama:", a.get("primaryName"), "· yayındaki gönderim:", (a.get("lastPublishedApplicationSubmission") or {}).get("id"))
    p = a.get("pendingApplicationSubmission")
    print("bekleyen gönderim:", p.get("id") if p else "yok")
    if p:
        s = call(tok, "GET", "/applications/%s/submissions/%s/status" % (APP, p["id"]))
        print("  durumu:", s.get("status"))
    end = dt.date.today(); start = end - dt.timedelta(days=30)
    r = call(tok, "GET", "/analytics/appacquisitions?applicationId=%s&startDate=%s&endDate=%s&aggregationLevel=day" % (APP, start, end), ok404=True)
    print("istatistik arayüzü:", "açık" if r is not None else "veri yok", "· satır:", len((r or {}).get("Value", [])))


def gonder(msix, notes_path):
    notes = json.load(open(notes_path, encoding="utf-8"))
    rn = {"tr": "\n".join(notes.get("surum", [])), "en": "\n".join(notes.get("surum_en", [])), "ar": "\n".join(notes.get("surum_ar", []))}
    tok = token()
    a = call(tok, "GET", "/applications/%s" % APP)
    p = a.get("pendingApplicationSubmission")
    if p:
        st = call(tok, "GET", "/applications/%s/submissions/%s/status" % (APP, p["id"])).get("status")
        if st in ("PendingCommit", "CommitFailed"):   # a draft (started in Partner Center or a failed try): it is replaced
            call(tok, "DELETE", "/applications/%s/submissions/%s" % (APP, p["id"])); print("eski taslak silindi:", p["id"], st)
        else:
            sys.exit("Store'da incelemede ya da yayımlanmakta olan bir gönderim var (%s, %s); o bitince yeniden deneyin." % (p["id"], st))
    sub = call(tok, "POST", "/applications/%s/submissions" % APP)
    sid, up = sub["id"], sub["fileUploadUrl"]
    name = os.path.basename(msix)
    for pk in sub.get("applicationPackages", []):
        pk["fileStatus"] = "PendingDelete"
    sub["applicationPackages"] = sub.get("applicationPackages", []) + [{"fileName": name, "fileStatus": "PendingUpload", "minimumDirectXVersion": "None", "minimumSystemRam": "None"}]
    for lang, L in (sub.get("listings") or {}).items():
        t = rn.get(lang.split("-")[0].lower())
        if t and "baseListing" in L:
            L["baseListing"]["releaseNotes"] = t[:1500]
    sub.pop("fileUploadUrl", None)
    # the package goes up in a zip, to the address the submission gave
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        z.write(msix, name)
    req = urllib.request.Request(up, data=buf.getvalue(), method="PUT", headers={"x-ms-blob-type": "BlockBlob"})
    with urllib.request.urlopen(req, timeout=900) as r:
        print("paket yüklendi:", name, r.status)
    call(tok, "PUT", "/applications/%s/submissions/%s" % (APP, sid), sub)
    call(tok, "POST", "/applications/%s/submissions/%s/commit" % (APP, sid))
    for _ in range(90):
        time.sleep(20)
        s = call(tok, "GET", "/applications/%s/submissions/%s/status" % (APP, sid))
        st = s.get("status")
        if st != "CommitStarted":
            break
    print("gönderim:", sid, "durum:", st)
    errs = (s.get("statusDetails") or {}).get("errors") or []
    for e in errs: print("  hata:", e.get("code"), e.get("details"))
    if st == "CommitFailed":
        sys.exit("Store gönderimi kabul etmedi")
    print("STORE GONDERILDI", sid)


def istatistik(out):
    tok = token()
    end = dt.date.today(); start = end - dt.timedelta(days=30)
    q = "applicationId=%s&startDate=%s&endDate=%s" % (APP, start, end)
    def get(path):
        r = call(tok, "GET", "/analytics/%s?%s" % (path, q), ok404=True)
        return (r or {}).get("Value", [])
    res = {"tarih": end.isoformat(), "edinme": get("appacquisitions"), "puan": get("ratings"), "yorum": get("reviews"), "hata": get("failurehits")}
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("edinme satırı:", len(res["edinme"]), "· puan:", len(res["puan"]), "· yorum:", len(res["yorum"]), "· hata:", len(res["hata"]))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "dene"
    if c == "dene": dene()
    elif c == "gonder": gonder(sys.argv[2], sys.argv[3])
    elif c == "istatistik": istatistik(sys.argv[2])
    else: sys.exit(__doc__)
