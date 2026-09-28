import pytest
from psycopg.conninfo import conninfo_to_dict
from pydantic import SecretStr, ValidationError

from rag.config import DatabaseConfig


def test_database_defaults_to_verified_tls() -> None:
    config = DatabaseConfig(PASSWORD=SecretStr("pw"))

    assert config.connect_kwargs() == {
        "host": "localhost",
        "port": 5432,
        "dbname": "rag",
        "user": "rag",
        "password": "pw",
        "sslmode": "verify-full",
        "sslrootcert": "system",
    }


def test_database_without_tls_has_no_root_cert() -> None:
    config = DatabaseConfig(PASSWORD=SecretStr("pw"), SSLMODE="disable")

    assert config.connect_kwargs()["sslmode"] == "disable"
    assert "sslrootcert" not in config.connect_kwargs()


def test_database_rejects_weak_sslmodes() -> None:
    with pytest.raises(ValidationError):
        DatabaseConfig(PASSWORD=SecretStr("pw"), SSLMODE="prefer")  # pyright: ignore[reportArgumentType]


def test_database_password_is_required() -> None:
    with pytest.raises(ValidationError):
        DatabaseConfig()  # pyright: ignore[reportCallIssue]


def test_conninfo_survives_special_characters_in_the_password() -> None:
    password = "p@ss w'rd=/:?"
    config = DatabaseConfig(PASSWORD=SecretStr(password), SSLMODE="disable")

    assert conninfo_to_dict(config.conninfo())["password"] == password
