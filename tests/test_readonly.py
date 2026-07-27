"""Test de sûreté : AUCUN connecteur ne peut passer/modifier/annuler d'ordre.

Ce test échoue si un jour quelqu'un ajoute une méthode d'exécution sur un
connecteur — c'est le filet de sécurité qui protège l'invariant central
du projet.
"""

from __future__ import annotations

import inspect

from src.connectors.aggregator import default_connectors
from src.connectors.base import ReadOnlyBrokerConnector

# Tout nom de méthode évoquant une écriture est interdit sur un connecteur.
FORBIDDEN = (
    "place_order", "submit_order", "create_order", "send_order",
    "cancel_order", "modify_order", "replace_order", "close_position",
    "buy", "sell", "order", "execute", "trade",
)

# Méthodes de lecture attendues sur l'interface.
READ_ONLY_API = {"get_balance", "get_positions", "get_order_history", "get_account_info"}


def test_interface_exposes_only_reads():
    public = {
        n for n in dir(ReadOnlyBrokerConnector)
        if not n.startswith("_") and callable(getattr(ReadOnlyBrokerConnector, n))
    }
    # is_available est un utilitaire de lecture ; le reste doit être l'API read-only.
    public.discard("is_available")
    assert public == READ_ONLY_API, f"API inattendue : {public}"


def test_no_connector_has_execution_method():
    for connector in default_connectors():
        names = [n.lower() for n in dir(connector) if not n.startswith("_")]
        for forbidden in FORBIDDEN:
            offenders = [n for n in names if n == forbidden]
            assert not offenders, (
                f"{connector.name} expose une méthode interdite : {offenders}"
            )


def test_all_connectors_subclass_readonly_base():
    for connector in default_connectors():
        assert isinstance(connector, ReadOnlyBrokerConnector)


def test_no_source_calls_execution_endpoints():
    """Vérifie qu'aucun adaptateur n'APPELLE un endpoint d'écriture connu.

    On cible la syntaxe d'appel (`token(`) et on ignore les commentaires,
    pour ne pas confondre une explication ("on n'appelle jamais X") avec
    un vrai appel.
    """
    import pkgutil
    import src.connectors as pkg

    # Motifs d'APPEL interdits (le token suivi d'une parenthèse).
    banned_calls = (
        "submit_order(", "create_order(", "createorder(",
        "placeorder(", "ordercreate(", "cancel_order(", "close_position(",
    )
    for mod in pkgutil.iter_modules(pkg.__path__):
        module = __import__(f"src.connectors.{mod.name}", fromlist=["x"])
        # On retire les commentaires ligne à ligne avant analyse.
        code_lines = [
            line.split("#", 1)[0]
            for line in inspect.getsource(module).splitlines()
        ]
        code = "\n".join(code_lines).lower()
        for call in banned_calls:
            assert call not in code, (
                f"{mod.name} contient un appel d'exécution : {call}"
            )
