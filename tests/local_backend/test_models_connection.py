import pytest
from pydantic import ValidationError

from local_backend.models.common import DbType
from local_backend.models.connection import (
    BigQueryConnectionParams,
    MySQLConnectionParams,
    PostgresConnectionParams,
)


class TestPostgresConnectionParams:
    def test_valid_params(self) -> None:
        params = PostgresConnectionParams(
            name="My Postgres",
            host="localhost",
            port=5432,
            database="mydb",
            username="admin",
            password="secret",
        )
        assert params.name == "My Postgres"
        assert params.db_type == DbType.POSTGRES
        assert params.host == "localhost"
        assert params.port == 5432
        assert params.database == "mydb"
        assert params.username == "admin"
        assert params.password == "secret"

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            PostgresConnectionParams(
                name="My Postgres",
                # host is missing
                port=5432,
                database="mydb",
                username="admin",
                password="secret",
            )

    def test_invalid_field_types(self) -> None:
        with pytest.raises(ValidationError):
            PostgresConnectionParams(
                name="My Postgres",
                host="localhost",
                port="not_a_number",
                database="mydb",
                username="admin",
                password="secret",
            )


class TestMySQLConnectionParams:
    def test_valid_params(self) -> None:
        params = MySQLConnectionParams(
            name="My MySQL",
            host="localhost",
            port=3306,
            database="mydb",
            username="root",
            password="secret",
        )
        assert params.name == "My MySQL"
        assert params.db_type == DbType.MYSQL
        assert params.host == "localhost"
        assert params.port == 3306
        assert params.database == "mydb"
        assert params.username == "root"
        assert params.password == "secret"

    def test_invalid_field_types(self) -> None:
        with pytest.raises(ValidationError):
            MySQLConnectionParams(
                name="My MySQL",
                host="localhost",
                port="not_a_number",
                database=12345,
                username="root",
                password="secret",
            )


class TestBigQueryConnectionParams:
    def test_valid_params(self) -> None:
        params = BigQueryConnectionParams(
            name="My BigQuery",
            project_id="project-123",
            service_account_json='{"type": "service_account"}',
        )
        assert params.name == "My BigQuery"
        assert params.db_type == DbType.BIGQUERY
        assert params.project_id == "project-123"
        assert params.service_account_json == '{"type": "service_account"}'

    def test_invalid_field_types(self) -> None:
        with pytest.raises(ValidationError):
            BigQueryConnectionParams(
                name="My BigQuery",
                project_id=12345,
                service_account_json='{"type": "service_account"}',
            )


class TestPortValidation:
    def test_port_below_range(self) -> None:
        with pytest.raises(ValidationError):
            PostgresConnectionParams(
                name="Bad Port",
                host="localhost",
                port=0,
                database="mydb",
                username="admin",
                password="secret",
            )

    def test_port_above_range(self) -> None:
        with pytest.raises(ValidationError):
            MySQLConnectionParams(
                name="Bad Port",
                host="localhost",
                port=70000,
                database="mydb",
                username="root",
                password="secret",
            )


class TestDbTypeValidation:
    def test_invalid_db_type(self) -> None:
        with pytest.raises(ValueError):
            DbType("oracle")
