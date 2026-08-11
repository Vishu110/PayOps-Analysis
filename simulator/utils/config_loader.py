from pathlib import Path

import yaml



PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(file_path: Path) -> dict:
    """
    Load a YAML configuration file and return it as a dictionary.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {file_path}"
        )

    with file_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if data is None:
        raise ValueError(
            f"Configuration file is empty: {file_path}"
        )

    return data


def load_countries() -> dict:
    """
    Load country reference data.
    """

    file_path = CONFIG_DIR / "reference" / "countries.yaml"

    return load_yaml(file_path)


def load_generator_config() -> dict:
    """
    Load simulation/generation rules.
    """

    file_path = CONFIG_DIR / "generator.yaml"

    return load_yaml(file_path)


def load_processors() -> dict:
    """
    Load processor reference data.
    """

    file_path = CONFIG_DIR / "reference" / "processors.yaml"

    return load_yaml(file_path)


def load_banks() -> dict:
    """
    Load issuing-bank reference data.
    """

    file_path = CONFIG_DIR / "reference" / "banks.yaml"

    return load_yaml(file_path)