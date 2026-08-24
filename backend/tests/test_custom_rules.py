"""Tests unitaires de la priorité des règles PCG personnalisées."""
from app.services.pcg_categorizer import PCGRule, categorize


class TestCustomRulesPriority:
    def test_regle_custom_prioritaire_sur_standard(self):
        """'EDF' matche normalement 606100 — une règle custom doit gagner."""
        custom = [PCGRule(["edf"], "601000", "Achats matières premières")]
        account, label = categorize("EDF", custom_rules=custom)
        assert account == "601000"
        assert label == "Achats matières premières"

    def test_custom_sans_match_retombe_sur_standard(self):
        custom = [PCGRule(["fournisseur xyz"], "601000", "Custom")]
        account, _ = categorize("ENGIE SA", custom_rules=custom)
        assert account == "606100"  # règle standard

    def test_sans_custom_comportement_standard(self):
        assert categorize("EDF")[0] == "606100"
        assert categorize("EDF", custom_rules=[])[0] == "606100"

    def test_custom_avec_frontieres_de_mots(self):
        custom = [PCGRule(["eau"], "606300", "Eau custom")]
        account, _ = categorize("SARL Bureaux & Co", custom_rules=custom)
        assert account != "606300"  # "bureaux" ne contient pas le MOT "eau"


class TestDisabledRules:
    def test_regle_desactivee_ignoree(self):
        from app.services.pcg_categorizer import DEFAULT_RULES
        edf_rule = next(r for r in DEFAULT_RULES if "edf" in r.keywords)
        account, _ = categorize("EDF", disabled_keys={edf_rule.key})
        assert account != "606100"  # la règle EDF ne s'applique plus

    def test_autres_regles_intactes(self):
        """Désactiver la règle Énergie ne touche pas la règle Gaz."""
        from app.services.pcg_categorizer import DEFAULT_RULES
        edf_rule = next(r for r in DEFAULT_RULES if "edf" in r.keywords)
        account, _ = categorize("GRDF", disabled_keys={edf_rule.key})
        assert account == "606200"

    def test_custom_jamais_desactivee_par_disabled_keys(self):
        """disabled_keys ne s'applique qu'aux règles standard."""
        custom = [PCGRule(["edf"], "601000", "Custom EDF")]
        account, _ = categorize("EDF", custom_rules=custom, disabled_keys={custom[0].key})
        assert account == "601000"

    def test_cle_inconnue_sans_effet(self):
        account, _ = categorize("EDF", disabled_keys={"999999:Inexistante"})
        assert account == "606100"
