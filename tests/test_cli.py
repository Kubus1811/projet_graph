from src.cli import main


def test_cli_valider_petit():
    assert main(["--donnees", "data/petit", "--operation", "valider"]) == 0


def test_cli_valider_realiste():
    assert main(["--donnees", "data/realiste", "--operation", "valider"]) == 0


def test_cli_resilience_petit():
    assert main(["--donnees", "data/petit", "--operation", "resilience"]) == 0


def test_cli_itineraires_petit():
    assert main(["--donnees", "data/petit", "--operation", "itineraires"]) == 0


def test_cli_generer(tmp_path):
    code = main([
        "--generer",
        "--sommets", "30",
        "--densite", "2.0",
        "--graine", "123",
        "--sortie", str(tmp_path / "cli_test_dir"),
    ])
    assert code == 0
    assert (tmp_path / "cli_test_dir" / "sites.csv").exists()
