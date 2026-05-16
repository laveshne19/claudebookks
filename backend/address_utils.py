"""Address utilities — parse sector / area / locality from a free-text address string."""
import re

# Match "Sector 17", "Sec 22", "Sec-22-C", "Sect 47", etc.
_SECTOR_RE = re.compile(r"(?:sec(?:tor|t|)\.?\s*[-\s]?)(\d{1,3}[a-z]?)", re.I)
# Common Punjab/Chandigarh/Mohali/Panchkula/Zirakpur area keywords
_KNOWN_AREAS = [
    "Industrial Area", "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5",
    "Phase 6", "Phase 7", "Phase 8", "Phase 9", "Phase 10", "Phase 11",
    "Manimajra", "Maloya", "Mauli Jagran", "Dhanas", "Khuda Lahora",
    "Burail", "Hallomajra", "Bapu Dham", "Ram Darbar",
    "Zirakpur", "Dera Bassi", "Lalru", "Banur", "Kharar",
    "Mohali", "Panchkula", "Pinjore", "Kalka", "Baltana", "Mullanpur",
    "Mani Majra", "Sukhna Lake",
]
_AREA_RE = re.compile(r"\b(" + "|".join(re.escape(a) for a in _KNOWN_AREAS) + r")\b", re.I)


def normalize_area(address: str = "", city: str = "", attention: str = "") -> str:
    """Return the best sector/area label from an address string.

    Priority:
    1. Sector number from address
    2. Known area keyword from address
    3. City (if not empty and not generic)
    """
    text = " ".join(filter(None, [address or "", attention or ""]))
    if text:
        m = _SECTOR_RE.search(text)
        if m:
            return f"Sector {m.group(1).upper()}"
        m2 = _AREA_RE.search(text)
        if m2:
            return m2.group(1).title()
    c = (city or "").strip()
    if c and c.lower() not in ("mumbai", "—", "-", "na", "n/a"):
        return c
    return "—"


def full_address(ba: dict) -> str:
    """Compose a one-line full address from Zoho billing_address dict."""
    if not isinstance(ba, dict):
        return ""
    parts = [
        (ba.get("attention") or "").strip(),
        (ba.get("address") or "").strip(),
        (ba.get("street2") or "").strip(),
        (ba.get("city") or "").strip(),
        (ba.get("state") or "").strip(),
        (ba.get("zip") or "").strip(),
    ]
    return ", ".join([p for p in parts if p])


def state_from_gstin(gstin: str) -> str:
    """Best-effort state name from first 2 digits of GSTIN."""
    if not gstin or len(gstin) < 2:
        return ""
    code = gstin[:2]
    mapping = {
        "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
        "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
        "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar",
        "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland",
        "14": "Manipur", "15": "Mizoram", "16": "Tripura",
        "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
        "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh",
        "23": "Madhya Pradesh", "24": "Gujarat",
        "25": "Daman and Diu", "26": "Dadra and Nagar Haveli",
        "27": "Maharashtra", "28": "Andhra Pradesh (Old)",
        "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
        "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
        "35": "Andaman and Nicobar", "36": "Telangana", "37": "Andhra Pradesh",
        "38": "Ladakh",
    }
    return mapping.get(code, "")
