import pytest

from local_backend.models.tables import (
    BigQueryTable,
    MySQLTable,
    PostgresTable,
    TableIdentifier,
)


class TestFullName:
    def test_postgres_full_name(self) -> None:
        table = PostgresTable(schema_name="public", table_name="orders")
        assert table.full_name() == "public.orders"

    def test_mysql_full_name(self) -> None:
        table = MySQLTable(database="mydb", table_name="orders")
        assert table.full_name() == "mydb.orders"

    def test_bigquery_full_name(self) -> None:
        table = BigQueryTable(project="proj", dataset="ds", table_name="orders")
        assert table.full_name() == "proj.ds.orders"


class TestSerializationRoundtrip:
    def test_postgres_roundtrip(self) -> None:
        original = PostgresTable(schema_name="public", table_name="orders")
        data = original.to_dict()
        restored = TableIdentifier.from_dict(data)
        assert isinstance(restored, PostgresTable)
        assert restored.full_name() == original.full_name()
        assert restored.schema_name == original.schema_name
        assert restored.table_name == original.table_name

    def test_mysql_roundtrip(self) -> None:
        original = MySQLTable(database="mydb", table_name="orders")
        data = original.to_dict()
        restored = TableIdentifier.from_dict(data)
        assert isinstance(restored, MySQLTable)
        assert restored.full_name() == original.full_name()
        assert restored.database == original.database
        assert restored.table_name == original.table_name

    def test_bigquery_roundtrip(self) -> None:
        original = BigQueryTable(project="proj", dataset="ds", table_name="orders")
        data = original.to_dict()
        restored = TableIdentifier.from_dict(data)
        assert isinstance(restored, BigQueryTable)
        assert restored.full_name() == original.full_name()
        assert restored.project == original.project
        assert restored.dataset == original.dataset
        assert restored.table_name == original.table_name


class TestFromDict:
    def test_postgres_from_dict(self) -> None:
        data = {"db_type": "postgres", "schema_name": "public", "table_name": "users"}
        table = TableIdentifier.from_dict(data)
        assert isinstance(table, PostgresTable)
        assert table.schema_name == "public"
        assert table.table_name == "users"

    def test_mysql_from_dict(self) -> None:
        data = {"db_type": "mysql", "database": "mydb", "table_name": "users"}
        table = TableIdentifier.from_dict(data)
        assert isinstance(table, MySQLTable)
        assert table.database == "mydb"
        assert table.table_name == "users"

    def test_bigquery_from_dict(self) -> None:
        data = {"db_type": "bigquery", "project": "proj", "dataset": "ds", "table_name": "users"}
        table = TableIdentifier.from_dict(data)
        assert isinstance(table, BigQueryTable)
        assert table.project == "proj"
        assert table.dataset == "ds"
        assert table.table_name == "users"

    def test_invalid_db_type(self) -> None:
        with pytest.raises(ValueError):
            TableIdentifier.from_dict({"db_type": "oracle", "table_name": "foo"})
