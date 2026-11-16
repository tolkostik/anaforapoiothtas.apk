"""
Βάση ελληνικών προϊόντων στο κινητό (χωρίς internet).

Κατεβάζει από το Open Food Facts τα πιο δημοφιλή προϊόντα που πωλούνται στην Ελλάδα (σε σελίδες των 100,
με παύση ανάμεσα για να μην επιβαρύνεται η δωρεάν υπηρεσία) και τα αποθηκεύει συμπιεσμένα.
"""
import gzip
import json
import time
import urllib.parse

import food as F

FIELDS = ("code,product_name,product_name_el,generic_name,brands,quantity,nutriscore_grade,nutriscore_score,"
          "nova_group,additives_tags,nutriments,categories_tags,image_front_small_url,ingredients_text_el,"
          "ingredients_text,allergens_tags,traces_tags,labels_tags,ingredients_analysis_tags,serving_size,"
          "serving_quantity,emb_codes,countries_tags,packagings")
SIZES = {"Μικρή (≈1.000 προϊόντα)": 10, "Μεσαία (≈3.000)": 30, "Μεγάλη (≈6.000)": 60, "Πολύ μεγάλη (≈12.000)": 120,
         "Όλα τα ελληνικά (≈25.000+)": 260}
BEAUTY_PAGES = {10: 3, 30: 6, 60: 10, 120: 15, 260: 25}
_MEM = {"db": None}


def _path():
    return F.DATA_DIR / "greek_products.json.gz"


def info():
    try:
        meta = json.loads((F.DATA_DIR / "greek_products.meta.json").read_text(encoding="utf-8"))
        return meta
    except Exception:  # noqa: BLE001
        return None


def _load():
    if _MEM["db"] is None:
        try:
            with gzip.open(_path(), "rt", encoding="utf-8") as fh:
                _MEM["db"] = json.load(fh)
        except Exception:  # noqa: BLE001
            _MEM["db"] = {}
    return _MEM["db"]


def lookup(code):
    p = _load().get(F.clean_code(code))
    if p:
        p = dict(p)
        p.setdefault("kind", "food")
        p["db"] = {"beauty": "openbeautyfacts", "petfood": "openpetfoodfacts",
                   "general": "openproductsfacts"}.get(p["kind"], "openfoodfacts")
        p["sources"] = ["Βάση στο κινητό (Open Food Facts)"]
        p["_offline"] = True
    return p


def download(pages, progress=lambda done, total, n: None, stop=lambda: False):
    """Τρόφιμα (Open Food Facts) και καλλυντικά (Open Beauty Facts) που πωλούνται στην Ελλάδα."""
    db = {}
    plan = [("food", "https://world.openfoodfacts.org", pg) for pg in range(1, pages + 1)]
    extra = BEAUTY_PAGES.get(pages, 5)
    plan += [("beauty", "https://world.openbeautyfacts.org", pg) for pg in range(1, extra + 1)]
    plan += [("petfood", "https://world.openpetfoodfacts.org", pg) for pg in range(1, max(2, extra // 3) + 1)]
    plan += [("general", "https://world.openproductsfacts.org", pg) for pg in range(1, max(2, extra // 3) + 1)]
    finished = set()
    for i, (kind, base, page) in enumerate(plan, 1):
        if stop():
            break
        if kind in finished:
            continue
        q = {"countries_tags": "en:greece", "fields": FIELDS, "page_size": 100, "page": page,
             "sort_by": "unique_scans_n"}
        js = None
        for attempt in range(3):
            try:
                js = F._get(f"{base}/api/v2/search?" + urllib.parse.urlencode(q), timeout=30)
                break
            except Exception:  # noqa: BLE001
                time.sleep(3 + attempt * 4)
        if not js:
            continue
        prods = js.get("products") or []
        for p in prods:
            c = p.get("code")
            if c and c not in db:
                p["kind"] = kind
                db[c] = p
        progress(i, len(plan), len(db))
        if not prods:
            finished.add(kind)
        time.sleep(2.5)              # ευγενική χρήση της δωρεάν υπηρεσίας
    if not db:
        raise RuntimeError("Δεν κατέβηκαν προϊόντα (έλεγξε τη σύνδεση).")
    F.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = F.DATA_DIR / "greek_products.json.gz.tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(db, fh, ensure_ascii=False)
    import os
    os.replace(tmp, _path())
    meta = {"count": len(db), "date": time.strftime("%d/%m/%Y"), "size_kb": int(_path().stat().st_size / 1024)}
    (F.DATA_DIR / "greek_products.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    _MEM["db"] = db
    return meta


def delete():
    for f in ("greek_products.json.gz", "greek_products.meta.json"):
        try:
            (F.DATA_DIR / f).unlink()
        except OSError:
            pass
    _MEM["db"] = {}


def _fold(t):
    import unicodedata
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


def search(term, limit=40):
    """Αναζήτηση με όνομα/μάρκα μέσα στη βάση του κινητού (άμεση, χωρίς internet, χωρίς τόνους)."""
    words = [w for w in _fold(term).split() if len(w) >= 2]
    if not words:
        return []
    out = []
    for p in _load().values():
        hay = _fold(" ".join(str(p.get(k) or "") for k in ("product_name_el", "product_name", "brands",
                                                            "generic_name")))
        if all(w in hay for w in words):
            q = dict(p)
            q.setdefault("kind", "food")
            q["_offline"] = True
            out.append(q)
            if len(out) >= limit:
                break
    return out


# ------------------------------------------------------------------ εξερεύνηση ανά κατηγορία
CATEGORIES = [
    ("Γιαούρτια", "en:yogurts", "food"), ("Γάλα", "en:milks", "food"), ("Τυριά", "en:cheeses", "food"),
    ("Αυγά", "en:eggs", "food"), ("Κρέας", "en:meats", "food"), ("Αλλαντικά", "en:prepared-meats", "food"),
    ("Ψάρια & θαλασσινά", "en:seafood", "food"), ("Κονσέρβες ψαριών", "en:canned-fishes", "food"),
    ("Φρούτα & λαχανικά", "en:fruits-and-vegetables-based-foods", "food"), ("Κατεψυγμένα", "en:frozen-foods", "food"),
    ("Έτοιμα γεύματα", "en:meals", "food"), ("Ψωμί & φρυγανιές", "en:breads", "food"),
    ("Δημητριακά πρωινού", "en:breakfast-cereals", "food"), ("Ζυμαρικά", "en:pastas", "food"),
    ("Ρύζι", "en:rices", "food"), ("Όσπρια", "en:legumes", "food"), ("Ξηροί καρποί", "en:nuts", "food"),
    ("Ελαιόλαδο", "en:olive-oils", "food"), ("Ελιές", "en:olives", "food"), ("Σάλτσες", "en:sauces", "food"),
    ("Μέλι & αλείμματα", "en:spreads", "food"), ("Μπισκότα", "en:biscuits", "food"),
    ("Σοκολάτες", "en:chocolates", "food"), ("Γλυκά & κέικ", "en:cakes", "food"), ("Παγωτά", "en:ice-creams", "food"),
    ("Αλμυρά σνακ", "en:salty-snacks", "food"), ("Χυμοί", "en:fruit-juices", "food"), ("Αναψυκτικά", "en:sodas", "food"),
    ("Νερά", "en:waters", "food"), ("Καφές", "en:coffees", "food"), ("Τσάι & αφεψήματα", "en:teas", "food"),
    ("Κρασιά", "en:wines", "food"), ("Μπύρες", "en:beers", "food"), ("Βρεφικές τροφές", "en:baby-foods", "food"),
    ("Χωρίς γλουτένη", "en:gluten-free", "food"),
    ("Σαμπουάν", "en:shampoos", "beauty"), ("Αφρόλουτρα", "en:shower-gels", "beauty"),
    ("Οδοντόκρεμες", "en:toothpastes", "beauty"), ("Αποσμητικά", "en:deodorants", "beauty"),
    ("Κρέμες προσώπου", "en:face-creams", "beauty"), ("Αντηλιακά", "en:sunscreens", "beauty"),
    ("Τροφές σκύλου", "en:dog-food", "petfood"), ("Τροφές γάτας", "en:cat-food", "petfood"),
]

_GRADE = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}


def category_counts():
    db = _load()
    out = {}
    for name, tag, _ in CATEGORIES:
        out[name] = sum(1 for p in db.values() if tag in (p.get("categories_tags") or []) or
                        tag in (p.get("labels_tags") or []))
    return out


def top_in_category(tag, limit=40):
    """Τα προϊόντα μιας κατηγορίας από τη βάση στο κινητό, τα καλύτερα πρώτα (Nutri-Score, μετά δημοφιλία)."""
    rows = []
    for p in _load().values():
        if tag in (p.get("categories_tags") or []) or tag in (p.get("labels_tags") or []):
            q = dict(p)
            q.setdefault("kind", "food")
            q["_offline"] = True
            g = _GRADE.get(str(q.get("nutriscore_grade") or "").lower(), 5)
            rows.append((g, q.get("nutriscore_score") if isinstance(q.get("nutriscore_score"), (int, float)) else 99, q))
    rows.sort(key=lambda t: (t[0], t[1]))
    return [q for _, _, q in rows[:limit]]


def all_products():
    for p in _load().values():
        q = dict(p)
        q.setdefault("kind", "food")
        q["_offline"] = True
        yield q
