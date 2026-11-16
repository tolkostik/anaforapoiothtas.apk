"""
Νηστεία (Ορθόδοξη παράδοση): αν ένα προϊόν είναι νηστίσιμο, και τι νηστεία ισχύει σήμερα.

Βαθμίδες (από την αυστηρότερη):
  ξηροφαγία (χωρίς λάδι)  <  λάδι & οστρακοειδή  <  ψάρι  <  κατάλυση (όλα)
Το προϊόν παίρνει τη βαθμίδα που χρειάζεται για να φαγωθεί.
"""
import datetime
import re

import food as F

LEVELS = {
    0: ("Νηστίσιμο, και χωρίς λάδι", (0.05, 0.6, 0.35, 1)),
    1: ("Νηστίσιμο (με λάδι)", (0.2, 0.68, 0.3, 1)),
    2: ("Τρώγεται όταν καταλύεται ψάρι", (0.15, 0.55, 0.85, 1)),
    3: ("Όχι νηστίσιμο", (0.85, 0.25, 0.2, 1)),
}

MEAT = ("κρέας", "κρεατ", "χοιρ", "μοσχ", "βοδιν", "αρνί", "αρνίσ", "κατσικ", "κοτόπουλ", "κοτοπουλ", "γαλοπούλ",
        "πάπια", "ζαμπόν", "μπέικον", "λουκάνικ", "σαλάμ", "μορταδέλ", "παστουρμ", "σουτζούκ", "γύρο", "ζελατίνη",
        "λαρδί", "ζωικό λίπος", "πανσέτα", "προσούτο", "ζωμός κοτ", "ζωμός βοδ",
        "meat", "pork", "beef", "chicken", "turkey", "lamb", "veal", "ham", "bacon", "sausage", "salami", "gelatin",
        "gelatine", "lard", "tallow", "duck", "e441", "e120", "carmine", "κοχενίλ")
DAIRY = ("γάλα", "γάλακτ", "γαλακτ", "βούτυρ", "τυρί", "τυριού", "φέτα", "γιαούρτ", "κρέμα γάλ", "ορός γάλακτος",
         "λακτόζ", "καζεΐν", "καζειν", "κεφαλοτύρ", "γραβιέρ", "μυζήθρ", "ανθότυρ",
         "milk", "butter", "cheese", "cream", "yogurt", "yoghurt", "whey", "lactose", "casein", "ghee")
EGG = ("αυγ", "αβγ", "λεκιθίνη αυγ", "egg", "albumin", "αλβουμίν")
FISH = ("ψάρ", "τόνο", "τόνος", "σολομ", "σαρδέλ", "γαύρ", "αντζούγ", "μπακαλιάρ", "σκουμπρ", "ρέγκ", "πέστροφ",
        "τσιπούρ", "λαβράκ", "αυγοτάραχ", "ταραμ", "χαβιάρ", "ιχθυέλαιο", "μουρουνέλαιο",
        "fish", "tuna", "salmon", "sardine", "anchov", "cod", "mackerel", "herring", "trout", "roe", "caviar")
SHELLFISH = ("γαρίδ", "καλαμάρ", "χταπόδ", "σουπι", "μύδι", "στρείδ", "κυδών", "αστακ", "καραβίδ", "καβούρ", "σαλιγκ",
             "shrimp", "prawn", "squid", "octopus", "cuttlefish", "mussel", "oyster", "clam", "lobster", "crab",
             "crustacean", "molluscs")
OIL = ("λάδι", "έλαιο", "ελαιόλαδ", "ηλιέλαιο", "φυτικά λίπη", "φυτικό λίπος", "μαργαρίν", "ταχίν",
       "oil", "fat", "margarine", "tahini")
WINE = ("κρασί", "οίνος", "οίνου", "μπύρα", "ζύθος", "ρακί", "τσίπουρ", "ούζο", "λικέρ", "wine", "beer", "liqueur")


def _has(text, words):
    return any(w in text for w in words)


def _neg(text, word):
    """«χωρίς γάλα», «δεν περιέχει αυγά», «ίχνη…» δεν μετράνε ως συστατικό."""
    return re.search(r"(χωρίς|δεν περιέχει|free|μπορεί να περιέχει|ίχνη)[^,.;]{0,25}" + re.escape(word), text)


# φράσεις που μοιάζουν με ζωικά αλλά δεν είναι (αφαιρούνται πριν τον έλεγχο)
SAFE = ("κακαοβούτυρ", "βούτυρο κακάο", "φυστικοβούτυρ", "βούτυρο φυστικ", "βούτυρο αμυγδάλ", "βούτυρο καριτέ",
        "cocoa butter", "peanut butter", "shea butter", "almond butter", "γάλα καρύδας", "γάλα αμυγδάλ", "γάλα σόγιας",
        "γάλα βρώμης", "γάλα ρυζιού", "coconut milk", "almond milk", "soy milk", "oat milk", "rice milk",
        "γαλακτωματ", "γαλακτικ", "lactic", "emulsif", "κρέμα καρύδας", "coconut cream", "κρέμα βαλσάμικ",
        "cream of tartar", "κρεμόριο", "τυρί σόγιας", "φυτικό τυρί", "vegan cheese", "eggplant", "fish sauce free")
_L = "a-zα-ωάέήίόύώϊϋΐΰ"


def _contains(text, words):
    t = text
    for sfe in SAFE:
        t = t.replace(sfe, " ")
    for w in words:
        for m in re.finditer(r"(?<![" + _L + r"])" + re.escape(w) + r"[" + _L + r"]*", t):
            if not _neg(t, w):
                return m.group(0)
    return None


def check(p):
    """Επιστρέφει dict: level (0-3 ή None αν άγνωστο), label, color, reasons, confidence."""
    kind = p.get("kind", "food")
    if kind not in ("food",):
        return None
    tags = set(p.get("ingredients_analysis_tags") or []) | set(p.get("labels_tags") or [])
    al = set(p.get("allergens_tags") or [])
    text = (F.ingredients_text(p) or "").lower()
    name = (F.name_of(p) or "").lower() + " " + " ".join(p.get("categories_tags") or []).lower()
    reasons = []
    level = None

    meat = _contains(text, MEAT) or (_contains(name, ("meats", "sausages", "hams", "chicken", "κρέας", "αλλαντ"))
                                     and not text)
    dairy = "en:milk" in al or _contains(text, DAIRY)
    egg = "en:eggs" in al or _contains(text, EGG)
    fish = "en:fish" in al or _contains(text, FISH)
    shell = "en:crustaceans" in al or "en:molluscs" in al or _contains(text, SHELLFISH)
    if not text and not al:
        # χωρίς συστατικά: μόνο από ετικέτες ή κατηγορία
        if "en:vegan" in tags:
            level = 1
            reasons.append("σήμανση vegan")
        elif "en:non-vegan" in tags:
            level = 3
            reasons.append("περιέχει ζωικά προϊόντα (κατά τη βάση)")
        elif _contains(name, ("dairies", "milks", "cheeses", "yogurts", "eggs", "meats", "γάλα", "τυρί", "γιαούρτι")):
            level = 3
            reasons.append("κατηγορία ζωικού προϊόντος")
        elif _contains(name, ("waters", "νερό", "fruit-juices", "χυμ", "legumes", "όσπρια", "pastas", "ζυμαρικ")):
            level = 1
            reasons.append("κατηγορία που συνήθως είναι νηστίσιμη")
        if level is None:
            return {"level": None, "label": "Δεν είναι γνωστό (λείπουν τα συστατικά)", "color": (0.55, 0.57, 0.62, 1),
                    "reasons": ["Πρόσθεσε φωτογραφία συστατικών για να ελεγχθεί."], "confidence": "—"}
        return _result(level, reasons, "χαμηλή")

    if meat:
        level = 3
        reasons.append(f"κρέας / ζωικό ({meat})" if isinstance(meat, str) else "κρέας")
    if dairy:
        level = 3
        reasons.append("γαλακτοκομικά" + (f" ({dairy})" if isinstance(dairy, str) else ""))
    if egg:
        level = 3
        reasons.append("αυγό" + (f" ({egg})" if isinstance(egg, str) else ""))
    if level is None and fish:
        level = 2
        reasons.append("ψάρι" + (f" ({fish})" if isinstance(fish, str) else ""))
    if level is None:
        oil = _contains(text, OIL)
        if shell:
            level = 1
            reasons.append("οστρακοειδή/μαλάκια (επιτρέπονται στη νηστεία)")
        if oil:
            level = 1
            reasons.append(f"περιέχει λάδι/λιπαρά ({oil})")
        if level is None:
            level = 0
            reasons.append("χωρίς ζωικά συστατικά και χωρίς λάδι")
        if _contains(text, ("μέλι", "honey")):
            reasons.append("περιέχει μέλι (θεωρείται νηστίσιμο)")
    wine = _contains(text, WINE)
    if wine:
        reasons.append(f"περιέχει αλκοόλ/κρασί ({wine})")
    traces = [t.split(":")[-1] for t in (p.get("traces_tags") or [])
              if t in ("en:milk", "en:eggs", "en:fish")]
    if traces and level is not None and level < 3:
        reasons.append("μπορεί να περιέχει ίχνη: " + ", ".join(
            {"milk": "γάλα", "eggs": "αυγό", "fish": "ψάρι"}.get(t, t) for t in traces) + " (δεν αναιρεί τη νηστεία)")
    conf = "υψηλή" if len(text) > 30 else "μέτρια"
    return _result(level, reasons, conf)


def _result(level, reasons, conf):
    label, color = LEVELS[level]
    return {"level": level, "label": label, "color": color, "reasons": reasons, "confidence": conf}


# ------------------------------------------------------------------ ημερολόγιο
def orthodox_easter(year):
    """Ορθόδοξο Πάσχα (αλγόριθμος Meeus, Ιουλιανό → Γρηγοριανό)."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = (d + e + 114) % 31 + 1
    return datetime.date(year, month, day) + datetime.timedelta(days=13)


def today_fast(day=None):
    """(τίτλος, επιτρεπόμενη βαθμίδα 0-3, εξήγηση). 3 = κατάλυση εις πάντα."""
    d = day or datetime.date.today()
    E = orthodox_easter(d.year)
    td = datetime.timedelta
    wd = d.weekday()               # 0 = Δευτέρα
    md = (d.month, d.day)
    # ελεύθερες περίοδοι
    if datetime.date(d.year, 12, 25) <= d or d <= datetime.date(d.year, 1, 4):
        return "Δωδεκαήμερο", 3, "Κατάλυση εις πάντα, από τα Χριστούγεννα ως τις 4 Ιανουαρίου."
    if E <= d <= E + td(days=6):
        return "Διακαινήσιμος εβδομάδα", 3, "Κατάλυση εις πάντα την εβδομάδα μετά το Πάσχα."
    pent = E + td(days=49)
    if pent <= d <= pent + td(days=6):
        return "Εβδομάδα μετά την Πεντηκοστή", 3, "Κατάλυση εις πάντα."
    triodion = E - td(days=70)
    if triodion <= d <= triodion + td(days=6):
        return "Εβδομάδα Τελώνου και Φαρισαίου", 3, "Κατάλυση εις πάντα (Τριώδιο)."
    if E - td(days=55) <= d <= E - td(days=49):
        return "Τυρινή εβδομάδα", 2, "Χωρίς κρέας· επιτρέπονται γαλακτοκομικά, αυγά και ψάρι."
    # μεγάλες νηστείες
    clean_mon = E - td(days=48)
    if clean_mon <= d < E:
        if d == E - td(days=1):
            return "Μεγάλο Σάββατο", 1, "Λάδι επιτρέπεται, όχι ψάρι."
        if d == E - td(days=2):
            return "Μεγάλη Παρασκευή", 0, "Αυστηρή νηστεία (ξηροφαγία)."
        if md == (3, 25):
            return "Ευαγγελισμός (Μεγάλη Σαρακοστή)", 2, "Καταλύεται ψάρι."
        if d == E - td(days=7):
            return "Κυριακή των Βαΐων", 2, "Καταλύεται ψάρι."
        if wd in (5, 6):
            return "Μεγάλη Σαρακοστή (Σαββατοκύριακο)", 1, "Επιτρέπονται λάδι και οστρακοειδή."
        return "Μεγάλη Σαρακοστή", 0, "Καθημερινές: ξηροφαγία κατά την αυστηρή τάξη (πολλοί τρώνε με λάδι)."
    apostles_start = pent + td(days=8)
    if apostles_start <= d <= datetime.date(d.year, 6, 28):
        return ("Νηστεία των Αγίων Αποστόλων", 1 if wd in (2, 4) else 2,
                "Καταλύεται ψάρι, εκτός Τετάρτης και Παρασκευής (λάδι).")
    if datetime.date(d.year, 8, 1) <= d <= datetime.date(d.year, 8, 14):
        if md == (8, 6):
            return "Μεταμόρφωση (νηστεία Δεκαπενταύγουστου)", 2, "Καταλύεται ψάρι."
        return "Νηστεία Δεκαπενταύγουστου", 1 if wd in (5, 6) else 0, "Λάδι μόνο Σαββατοκύριακο· αλλιώς ξηροφαγία."
    if datetime.date(d.year, 11, 15) <= d <= datetime.date(d.year, 12, 24):
        if d >= datetime.date(d.year, 12, 18) or wd in (2, 4):
            return "Σαρανταήμερο Χριστουγέννων", 1, "Λάδι και οστρακοειδή (όχι ψάρι)."
        return "Σαρανταήμερο Χριστουγέννων", 2, "Καταλύεται ψάρι (εκτός Τετάρτης, Παρασκευής και από 18/12)."
    fixed = {(1, 5): "Παραμονή Θεοφανείων", (8, 29): "Αποτομή κεφαλής Προδρόμου", (9, 14): "Ύψωση του Τιμίου Σταυρού"}
    if md in fixed:
        return fixed[md], 1, "Ημέρα νηστείας (λάδι επιτρέπεται)."
    if wd in (2, 4):
        return ("Τετάρτη" if wd == 2 else "Παρασκευή"), 1, "Νηστεία Τετάρτης/Παρασκευής."
    return "Δεν είναι ημέρα νηστείας", 3, "Κατάλυση εις πάντα."


def verdict_today(p, day=None):
    """Μπορώ να το φάω σήμερα; (True/False/None, κείμενο)."""
    r = check(p)
    if not r or r["level"] is None:
        return None, ""
    title, allowed, _ = today_fast(day)
    if allowed >= 3:
        return True, f"Σήμερα ({title}): επιτρέπεται."
    ok = r["level"] <= allowed
    return ok, f"Σήμερα ({title}): " + ("ταιριάζει με τη νηστεία." if ok else "δεν ταιριάζει με τη νηστεία.")


NOTE = ("Ο έλεγχος γίνεται από τα συστατικά της βάσης και ακολουθεί την κοινή τυπική της Εκκλησίας. Για "
        "την προσωπική σου νηστεία, συμβουλέψου τον πνευματικό σου.")
