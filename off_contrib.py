"""
Συμπλήρωση προϊόντων στο Open Food Facts: φωτογραφίες (μπροστά, συστατικά, διατροφικός πίνακας) και όνομα.
Η αυτόματη ανάγνωση κειμένου του Open Food Facts (που διαβάζει και ελληνικά) συμπληρώνει μετά τα στοιχεία.
Χρειάζεται δωρεάν λογαριασμός στο openfoodfacts.org.
"""
import json
import ssl
import urllib.parse
import urllib.request
import uuid

import food as F

BASE = {"food": "https://world.openfoodfacts.org", "beauty": "https://world.openbeautyfacts.org",
        "petfood": "https://world.openpetfoodfacts.org", "general": "https://world.openproductsfacts.org",
        "electronics": "https://world.openproductsfacts.org", "medicine": "https://world.openproductsfacts.org"}
FIELDS = {"front": "Μπροστινή όψη", "ingredients": "Συστατικά", "nutrition": "Διατροφικός πίνακας"}
SIGNUP = "https://world.openfoodfacts.org/cgi/user.pl"


def creds():
    return F.get_setting("off_user", ""), F.get_setting("off_pass", "")


def set_creds(user, pw):
    F.set_setting("off_user", user.strip())
    F.set_setting("off_pass", pw)


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


def _post(url, fields, file_field=None, file_name=None, data=None, timeout=90):
    boundary = "----poiotita" + uuid.uuid4().hex
    body = bytearray()
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
    if file_field and data is not None:
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{file_name}\"\r\n"
                 f"Content-Type: image/jpeg\r\n\r\n").encode("utf-8")
        body += data + b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(url, data=bytes(body), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                          "User-Agent": F.UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        txt = r.read().decode("utf-8", "replace")
    try:
        return json.loads(txt)
    except ValueError:
        return {"raw": txt[:200]}


def upload_image(kind, code, field, jpeg_bytes):
    user, pw = creds()
    if not user or not pw:
        raise RuntimeError("Βάλε πρώτα τον λογαριασμό σου στο Open Food Facts (Εγώ → Συμβολή).")
    base = BASE.get(kind, BASE["food"])
    imagefield = f"{field}_el"
    res = _post(f"{base}/cgi/product_image_upload.pl",
                {"code": F.clean_code(code), "imagefield": imagefield, "user_id": user, "password": pw},
                file_field=f"imgupload_{imagefield}", file_name=f"{field}.jpg", data=jpeg_bytes)
    status = str(res.get("status", "")).lower()
    if status in ("status ok", "ok", "1") or res.get("status_code") == 0 or "imgid" in res or "image" in res:
        return True, "Η φωτογραφία ανέβηκε."
    if "raw" in res:
        return True, "Η φωτογραφία στάλθηκε."
    err = res.get("error") or res.get("status") or "άγνωστη απάντηση"
    return False, f"Η βάση απάντησε: {str(err)[:120]}"


def set_name(kind, code, name, brand=""):
    user, pw = creds()
    if not user or not pw:
        raise RuntimeError("Λείπει ο λογαριασμός Open Food Facts.")
    base = BASE.get(kind, BASE["food"])
    q = {"code": F.clean_code(code), "user_id": user, "password": pw, "lang": "el", "product_name_el": name}
    if brand:
        q["brands"] = brand
    req = urllib.request.Request(f"{base}/cgi/product_jqm2.pl", data=urllib.parse.urlencode(q).encode("utf-8"),
                                 method="POST", headers={"User-Agent": F.UA})
    with urllib.request.urlopen(req, timeout=40, context=_ctx()) as r:
        js = json.loads(r.read().decode("utf-8", "replace") or "{}")
    return js.get("status") == 1, js.get("status_verbose", "")
