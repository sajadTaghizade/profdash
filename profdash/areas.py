"""CS research areas, as defined by CSRankings.

Four groups, 27 areas. Each area lists the conferences CSRankings counts
toward it; a professor's area profile is the sum of their (author-adjusted)
paper counts per area over those conferences.

`next_tier` conferences are shown by CSRankings only on request, but they
are still real signal for "what does this person work on", so profdash
counts them.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Area:
    code: str            # CSRankings parent-area code (stored in professor_areas)
    title: str           # display name (stored in professors.area)
    group: str           # one of GROUPS
    confs: tuple[str, ...]
    next_tier: tuple[str, ...] = ()

    @property
    def all_confs(self) -> tuple[str, ...]:
        return self.confs + self.next_tier


GROUPS: tuple[str, ...] = ("AI", "Systems", "Theory", "Interdisciplinary")

AREAS: tuple[Area, ...] = (
    # --- AI -----------------------------------------------------------------
    Area("ai", "AI", "AI", ("aaai", "ijcai")),
    Area("vision", "Vision", "AI", ("cvpr", "eccv", "iccv")),
    Area("mlmining", "ML", "AI", ("icml", "iclr", "nips"), ("kdd",)),
    Area("nlp", "NLP", "AI", ("acl", "emnlp", "naacl")),
    Area("inforet", "Web+IR", "AI", ("sigir", "www")),
    # --- Systems ------------------------------------------------------------
    Area("arch", "Architecture", "Systems", ("asplos", "isca", "micro"), ("hpca",)),
    Area("comm", "Networks", "Systems", ("sigcomm", "nsdi")),
    Area("sec", "Security", "Systems", ("ccs", "oakland", "usenixsec"), ("ndss",)),
    Area("mod", "Databases", "Systems", ("sigmod", "vldb"), ("icde", "pods")),
    Area("da", "EDA", "Systems", ("dac", "iccad")),
    Area("bed", "Embedded", "Systems", ("emsoft", "rtas", "rtss")),
    Area("hpc", "HPC", "Systems", ("sc", "hpdc", "ics")),
    Area("mobile", "Mobile", "Systems", ("mobicom", "mobisys", "sensys")),
    Area("metrics", "Metrics", "Systems", ("imc", "sigmetrics")),
    Area("ops", "OS", "Systems", ("sosp", "osdi"), ("eurosys", "fast", "usenixatc")),
    Area("plan", "PL", "Systems", ("popl", "pldi"), ("icfp", "oopsla")),
    Area("soft", "SE", "Systems", ("fse", "icse"), ("ase", "issta")),
    # --- Theory -------------------------------------------------------------
    Area("act", "Algorithms", "Theory", ("focs", "soda", "stoc")),
    Area("crypt", "Crypto", "Theory", ("crypto", "eurocrypt")),
    Area("log", "Logic", "Theory", ("cav", "lics")),
    # --- Interdisciplinary --------------------------------------------------
    Area("bio", "Comp. Bio", "Interdisciplinary", ("ismb", "recomb")),
    Area("graph", "Graphics", "Interdisciplinary",
         ("siggraph", "siggraph-asia"), ("eurographics",)),
    Area("csed", "CS Education", "Interdisciplinary", ("sigcse",)),
    Area("ecom", "Econ+Comp", "Interdisciplinary", ("ec", "wine")),
    Area("chi", "HCI", "Interdisciplinary", ("chiconf", "ubicomp", "uist")),
    Area("robotics", "Robotics", "Interdisciplinary", ("icra", "iros", "rss")),
    Area("visualization", "Visualization", "Interdisciplinary", ("vis", "vr")),
)

BY_CODE: dict[str, Area] = {a.code: a for a in AREAS}
CONF_TO_AREA: dict[str, str] = {c: a.code for a in AREAS for c in a.all_confs}
_TITLE_TO_CODE = {a.title.lower(): a.code for a in AREAS}


def areas_in_group(group: str) -> list[Area]:
    return [a for a in AREAS if a.group.lower() == group.lower()]


def resolve(token: str) -> list[Area]:
    """Resolve a user-supplied token (area code, area title, or group name)
    to areas. A group is written `group:systems` (or just `systems`, except
    `ai`, which is also an area code). Raises ValueError listing valid choices when it matches nothing."""
    t = token.strip().lower()
    if t.startswith("group:"):          # "ai" alone means the AI *area*
        grp = areas_in_group(t[6:])
        if grp:
            return grp
    elif t in BY_CODE:
        return [BY_CODE[t]]
    if t in _TITLE_TO_CODE:
        return [BY_CODE[_TITLE_TO_CODE[t]]]
    grp = areas_in_group(t)
    if grp:
        return grp
    valid = ", ".join(sorted(BY_CODE) + [f"group:{g.lower()}" for g in GROUPS])
    raise ValueError(f"unknown area {token!r}; valid: {valid}")


def primary_area(scores: dict[str, float]) -> Area | None:
    """Area with the highest paper score (ties broken by AREAS order)."""
    best, best_v = None, 0.0
    for a in AREAS:
        v = scores.get(a.code, 0.0)
        if v > best_v:
            best, best_v = a, v
    return best


# DBLP venue strings per area, as they appear in the DBLP search API `venue`
# field (matched case-insensitively, with volume suffixes like "(1)" ignored —
# see profdash.venues). `strong` = the CSRankings conferences for the area,
# `moderate` = well-regarded second-tier conferences and journals.
VENUES: dict[str, dict[str, tuple[str, ...]]] = {
    # --- AI -----------------------------------------------------------------
    "ai": {
        "strong": ("AAAI", "IJCAI"),
        "moderate": ("ECAI", "AAMAS", "KR", "UAI", "Artif. Intell.",
                     "J. Artif. Intell. Res."),
    },
    "vision": {
        "strong": ("CVPR", "ICCV", "ECCV"),
        "moderate": ("BMVC", "WACV", "3DV", "IEEE Trans. Pattern Anal. Mach. Intell.",
                     "Int. J. Comput. Vis."),
    },
    "mlmining": {
        "strong": ("NeurIPS", "NIPS", "ICML", "ICLR", "KDD"),
        "moderate": ("AISTATS", "UAI", "COLT", "J. Mach. Learn. Res.",
                     "Trans. Mach. Learn. Res.", "ICDM", "SDM", "WSDM", "CIKM"),
    },
    "nlp": {
        "strong": ("ACL", "EMNLP", "NAACL-HLT", "NAACL"),
        "moderate": ("EACL", "COLING", "CoNLL", "Trans. Assoc. Comput. Linguistics",
                     "ACL (Findings)", "EMNLP (Findings)", "NAACL (Findings)",
                     "Comput. Linguistics"),
    },
    "inforet": {
        "strong": ("SIGIR", "WWW"),
        "moderate": ("CIKM", "WSDM", "ECIR", "RecSys", "ACM Trans. Inf. Syst."),
    },
    # --- Systems ------------------------------------------------------------
    "arch": {
        "strong": ("ISCA", "MICRO", "ASPLOS", "HPCA"),
        "moderate": ("PACT", "IEEE Comput. Archit. Lett.", "ACM Trans. Archit. Code Optim.",
                     "ICS", "DATE"),
    },
    "comm": {
        "strong": ("SIGCOMM", "NSDI"),
        "moderate": ("CoNEXT", "INFOCOM", "HotNets", "IEEE/ACM Trans. Netw.",
                     "Proc. ACM Netw.", "ICNP"),
    },
    "sec": {
        "strong": ("CCS", "SP", "USENIX Security", "USENIX Security Symposium", "NDSS"),
        "moderate": ("EuroS&P", "ACSAC", "RAID", "AsiaCCS", "ESORICS",
                     "Proc. Priv. Enhancing Technol.", "IEEE Trans. Inf. Forensics Secur.",
                     "IEEE Trans. Dependable Secur. Comput."),
    },
    "mod": {
        "strong": ("SIGMOD Conference", "Proc. ACM Manag. Data", "Proc. VLDB Endow.",
                   "ICDE", "PODS"),
        "moderate": ("EDBT", "CIDR", "ICDT", "VLDB J.", "IEEE Trans. Knowl. Data Eng.",
                     "CIKM"),
    },
    "da": {
        "strong": ("DAC", "ICCAD"),
        "moderate": ("DATE", "ASP-DAC", "ISPD",
                     "IEEE Trans. Comput. Aided Des. Integr. Circuits Syst."),
    },
    "bed": {
        "strong": ("EMSOFT", "RTAS", "RTSS"),
        "moderate": ("ECRTS", "CODES+ISSS", "LCTES", "ICCPS",
                     "ACM Trans. Embed. Comput. Syst."),
    },
    "hpc": {
        "strong": ("SC", "HPDC", "ICS"),
        "moderate": ("PPoPP", "IPDPS", "ICPP", "CLUSTER", "SPAA",
                     "IEEE Trans. Parallel Distributed Syst."),
    },
    "mobile": {
        "strong": ("MobiCom", "MobiSys", "SenSys"),
        "moderate": ("IPSN", "INFOCOM", "IEEE Trans. Mob. Comput.",
                     "Proc. ACM Interact. Mob. Wearable Ubiquitous Technol."),
    },
    "metrics": {
        "strong": ("IMC", "SIGMETRICS", "Proc. ACM Meas. Anal. Comput. Syst."),
        "moderate": ("PAM", "Perform. Evaluation", "MASCOTS"),
    },
    "ops": {
        "strong": ("SOSP", "OSDI", "EuroSys", "FAST", "USENIX ATC",
                   "USENIX Annual Technical Conference"),
        "moderate": ("SoCC", "VEE", "HotOS", "Middleware", "ACM Trans. Comput. Syst.",
                     "ACM Trans. Storage"),
    },
    "plan": {
        "strong": ("POPL", "PLDI", "Proc. ACM Program. Lang.", "ICFP", "OOPSLA"),
        "moderate": ("ECOOP", "ESOP", "CC", "CGO", "SAS",
                     "ACM Trans. Program. Lang. Syst."),
    },
    "soft": {
        "strong": ("ICSE", "ESEC/SIGSOFT FSE", "SIGSOFT FSE", "Proc. ACM Softw. Eng.",
                   "ASE", "ISSTA"),
        "moderate": ("MSR", "ICSME", "SANER", "IEEE Trans. Software Eng.",
                     "ACM Trans. Softw. Eng. Methodol.", "Empir. Softw. Eng."),
    },
    # --- Theory -------------------------------------------------------------
    "act": {
        "strong": ("STOC", "FOCS", "SODA"),
        "moderate": ("ICALP", "ESA", "SoCG", "ITCS", "APPROX/RANDOM", "STACS", "CCC",
                     "PODC", "SPAA", "SIAM J. Comput.", "J. ACM", "ACM Trans. Algorithms"),
    },
    "crypt": {
        "strong": ("CRYPTO", "EUROCRYPT"),
        "moderate": ("ASIACRYPT", "TCC", "PKC", "CHES", "J. Cryptol.",
                     "IACR Trans. Cryptogr. Hardw. Embed. Syst."),
    },
    "log": {
        "strong": ("LICS", "CAV"),
        "moderate": ("TACAS", "CSL", "FSCD", "CONCUR", "VMCAI", "IJCAR", "CADE", "FM",
                     "Log. Methods Comput. Sci.", "ACM Trans. Comput. Log."),
    },
    # --- Interdisciplinary --------------------------------------------------
    "bio": {
        "strong": ("ISMB", "RECOMB", "Bioinform."),
        "moderate": ("BCB", "WABI", "PLoS Comput. Biol.", "BMC Bioinform.",
                     "Nucleic Acids Res."),
    },
    "graph": {
        "strong": ("SIGGRAPH", "SIGGRAPH Asia", "ACM Trans. Graph.",
                   "Comput. Graph. Forum"),
        "moderate": ("I3D", "SCA", "Pacific Graphics", "Eurographics",
                     "IEEE Trans. Vis. Comput. Graph."),
    },
    "csed": {
        "strong": ("SIGCSE",),
        "moderate": ("ITiCSE", "ICER", "Koli Calling", "ACM Trans. Comput. Educ."),
    },
    "ecom": {
        "strong": ("EC", "WINE"),
        "moderate": ("SAGT", "AAMAS", "Games Econ. Behav.",
                     "ACM Trans. Economics and Comput."),
    },
    "chi": {
        "strong": ("CHI", "UIST", "UbiComp",
                   "Proc. ACM Interact. Mob. Wearable Ubiquitous Technol."),
        "moderate": ("CSCW", "DIS", "IUI", "Proc. ACM Hum. Comput. Interact.",
                     "ACM Trans. Comput. Hum. Interact."),
    },
    "robotics": {
        "strong": ("ICRA", "IROS", "Robotics: Science and Systems"),
        "moderate": ("CoRL", "HRI", "IEEE Robotics Autom. Lett.", "IEEE Trans. Robotics",
                     "Int. J. Robotics Res."),
    },
    "visualization": {
        "strong": ("IEEE VIS", "VR", "IEEE VR", "IEEE Trans. Vis. Comput. Graph."),
        "moderate": ("EuroVis", "PacificVis", "ISMAR"),
    },
}


def venue_tiers(tokens: list[str]) -> tuple[list[str], list[str]]:
    """(strong, moderate) DBLP venue strings for the given area tokens
    (codes, names or group:<name>). A venue strong in any selected area is
    never listed as moderate."""
    strong: list[str] = []
    moderate: list[str] = []
    for tok in tokens:
        for a in resolve(tok):
            v = VENUES.get(a.code, {})
            strong += [s for s in v.get("strong", ()) if s not in strong]
            moderate += [m for m in v.get("moderate", ()) if m not in moderate]
    moderate = [m for m in moderate if m not in strong]
    return strong, moderate
