#!/usr/bin/env python3
"""App Store Connect API anahtarını sınar: imzalı kısa ömürlü belgeyle uygulama listesini okur; anahtar ve kimlikler
yazdırılmaz, yalnız uygulamaların adı ve paket kimliği."""
import base64, json, os, time, urllib.request
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

kid, iss, p8 = os.environ["KID"], os.environ["ISS"], os.environ["P8"]
key = serialization.load_pem_private_key(p8.encode(), password=None)
b = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=")
head = b(json.dumps({"alg": "ES256", "kid": kid, "typ": "JWT"}).encode())
now = int(time.time())
body = b(json.dumps({"iss": iss, "iat": now, "exp": now + 600, "aud": "appstoreconnect-v1"}).encode())
der = key.sign(head + b"." + body, ec.ECDSA(hashes.SHA256()))
r, s = utils.decode_dss_signature(der)
tok = (head + b"." + body + b"." + b(r.to_bytes(32, "big") + s.to_bytes(32, "big"))).decode()
req = urllib.request.Request("https://api.appstoreconnect.apple.com/v1/apps?fields[apps]=name,bundleId", headers={"Authorization": "Bearer " + tok})
with urllib.request.urlopen(req, timeout=30) as resp:
    d = json.load(resp)
for a in d.get("data", []):
    print("UYGULAMA:", a["attributes"]["name"], a["attributes"]["bundleId"])
print("TAKIM KIMLIGI UZUNLUGU:", len(os.environ.get("TEAM", "")))
