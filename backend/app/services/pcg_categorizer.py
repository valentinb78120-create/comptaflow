"""
PCG (Plan Comptable Général) automatic categorization.

Rules are evaluated in order; first match wins.
The ruleset is intentionally simple dict-based so it can be stored in DB in V2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PCGRule:
    """A single categorization rule."""
    keywords: list[str]
    account: str
    label: str

    @property
    def key(self) -> str:
        """Identifiant stable de la règle (désactivation par cabinet)."""
        return f"{self.account}:{self.label}"


# ---------------------------------------------------------------------------
# Default rule set — extend freely, order matters (first match wins)
# ---------------------------------------------------------------------------
DEFAULT_RULES: list[PCGRule] = [
    # Énergie & fluides
    PCGRule(["edf", "engie", "électricité", "electricite", "courant électrique", "direct energie", "total energies"], "606100", "Énergie électrique"),
    PCGRule(["gaz", "grdf", "siplec", "butagaz"], "606200", "Gaz"),
    PCGRule(["eau", "saur", "veolia", "suez"], "606300", "Eau"),

    # Télécom & internet
    PCGRule(["orange", "sfr", "bouygues telecom", "free", "iliad", "numericable", "ovh", "téléphone", "telephone", "internet", "fibre"], "626000", "Frais postaux et télécom"),

    # Loyer & charges locatives
    PCGRule(["loyer", "bail", "location bureau", "location local", "charges locatives"], "613000", "Loyers"),
    PCGRule(["charges copropriété", "syndic"], "614000", "Charges de copropriété"),

    # Assurances
    PCGRule(["axa", "allianz", "maif", "mma", "groupama", "covea", "matmut", "assurance", "mutuelle"], "616000", "Primes d'assurance"),

    # Fournitures & consommables
    PCGRule(["amazon business", "lyreco", "staples", "raja", "fournitures bureau", "papeterie"], "606400", "Fournitures de bureau"),
    PCGRule(["carburant", "essence", "gazole", "diesel", "total", "bp station", "shell"], "606110", "Carburants"),
    PCGRule(["fournitures atelier", "consommables"], "606500", "Fournitures atelier/chantier"),

    # Transport & déplacements
    PCGRule(["sncf", "oui.sncf", "tgv", "ter ", "transilien", "ratp", "navigo"], "625100", "Voyages et déplacements — train"),
    PCGRule(["air france", "easyjet", "ryanair", "transavia", "volotea", "corsair", "billet avion"], "625100", "Voyages et déplacements — avion"),
    PCGRule(["uber", "bolt", "taxi", "g7", "vtc"], "625200", "Taxis et VTC"),
    PCGRule(["parking", "autoroute", "péage", "vinci autoroutes", "sanef"], "625600", "Frais de stationnement et péages"),

    # Restauration & repas
    PCGRule(["restaurant", "brasserie", "bistrot", "mcdonald", "burger king", "sodexo", "edenred", "repas client", "déjeuner client"], "625700", "Réceptions et repas d'affaires"),

    # Hébergement
    PCGRule(["hotel", "hôtel", "ibis", "novotel", "accor", "marriott", "booking.com", "airbnb", "nuit"], "625100", "Hébergement"),

    # Informatique & logiciels
    PCGRule(["microsoft", "office 365", "azure", "google workspace", "slack", "notion", "adobe", "logiciel", "abonnement saas", "licence"], "618500", "Logiciels et licences"),
    PCGRule(["apple", "dell", "hp ", "lenovo", "logitech", "ordinateur", "matériel informatique", "écran", "clavier"], "218300", "Matériel informatique"),

    # Honoraires & prestations
    PCGRule(["honoraires", "consultant", "prestation", "freelance", "avocat", "expert-comptable", "commissaire"], "622000", "Honoraires et rémunérations diverses"),
    PCGRule(["intérim", "interim", "adecco", "manpower", "randstad"], "621100", "Personnel intérimaire"),

    # Publicité & marketing
    PCGRule(["publicité", "publicite", "marketing", "facebook ads", "google ads", "linkedin ads", "meta ads", "impression flyer", "agence communication"], "623100", "Publicité"),

    # Frais bancaires
    PCGRule(["frais bancaires", "commission bancaire", "agios", "frais tenue compte", "bnp paribas frais", "crédit agricole frais"], "627000", "Frais bancaires"),

    # Sous-traitance
    PCGRule(["sous-traitance", "sous traitance", "prestataire travaux"], "611000", "Sous-traitance générale"),

    # Entretien & réparations
    PCGRule(["entretien", "réparation", "maintenance", "dépannage"], "615000", "Entretien et réparations"),

    # Locations de matériel & leasing
    PCGRule(["leasing", "crédit-bail", "credit bail", "location longue durée", "lld", "location véhicule"], "612200", "Crédit-bail mobilier"),
    PCGRule(["location matériel", "location photocopieur", "location machine"], "613500", "Locations mobilières"),

    # Documentation & formation
    PCGRule(["abonnement presse", "documentation", "revue", "ouvrage professionnel"], "618100", "Documentation générale"),
    PCGRule(["formation", "séminaire", "webinar", "e-learning", "cpf"], "618800", "Formation professionnelle"),

    # Cotisations & adhésions
    PCGRule(["cotisation", "adhésion", "ordre des experts", "syndicat professionnel"], "628100", "Cotisations professionnelles"),

    # Affranchissement & courrier
    PCGRule(["la poste", "affranchissement", "chronopost", "colissimo", "dhl", "ups", "fedex"], "626100", "Frais postaux"),

    # Cloud & hébergement
    PCGRule(["aws", "amazon web services", "google cloud", "gcp", "scaleway", "ovhcloud", "hébergement web", "serveur dédié"], "618500", "Hébergement et services cloud"),

    # Nettoyage & sécurité des locaux
    PCGRule(["nettoyage", "ménage", "propreté", "onet"], "615600", "Nettoyage des locaux"),
    PCGRule(["gardiennage", "télésurveillance", "alarme", "securitas", "verisure"], "628800", "Gardiennage et surveillance"),

    # Véhicules
    PCGRule(["norauto", "feu vert", "garage", "contrôle technique", "pneus", "vidange"], "615500", "Entretien des véhicules"),

    # Commissions & frais de plateforme
    PCGRule(["stripe", "paypal", "commission plateforme", "frais de paiement"], "627800", "Frais sur moyens de paiement"),

    # Impôts & taxes courantes (hors IS)
    PCGRule(["cfe", "cotisation foncière", "cvae", "taxe foncière"], "635110", "Impôts locaux"),
]


def categorize(
    vendor_name: str,
    description: str = "",
    custom_rules: list[PCGRule] | None = None,
    disabled_keys: set[str] | None = None,
) -> tuple[str, str] | tuple[None, None]:
    """
    Return (pcg_account, pcg_label) for a vendor name + optional description.
    Returns (None, None) when no rule matches.

    Les règles personnalisées du cabinet (*custom_rules*) sont évaluées
    AVANT les règles par défaut — elles permettent de surcharger le standard.
    *disabled_keys* permet à un cabinet d'ignorer certaines règles standard.
    Matching insensible à la casse, mots entiers, sur fournisseur + description.
    """
    haystack = f"{vendor_name} {description}".lower()
    haystack = re.sub(r"\s+", " ", haystack)

    disabled = disabled_keys or set()
    active_defaults = [r for r in DEFAULT_RULES if r.key not in disabled]

    for rule in (custom_rules or []) + active_defaults:
        for keyword in rule.keywords:
            # Frontières de mots obligatoires : sans elles, "bureaux"
            # matcherait le mot-clé "eau" (606300 au lieu de 613000).
            pattern = r"(?<!\w)" + re.escape(keyword.lower().strip()) + r"(?!\w)"
            if re.search(pattern, haystack):
                return rule.account, rule.label

    return None, None


def get_all_rules() -> list[dict]:
    """Liste sérialisable des règles standard, avec leur clé stable."""
    return [
        {"key": r.key, "keywords": r.keywords, "account": r.account, "label": r.label}
        for r in DEFAULT_RULES
    ]


def is_valid_rule_key(key: str) -> bool:
    """La clé correspond-elle à une règle standard existante ?"""
    return any(r.key == key for r in DEFAULT_RULES)
