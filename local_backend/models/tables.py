from __future__ import annotations

from pydantic import BaseModel, Field

from local_backend.models.common import DbType


class TableIdentifier(BaseModel):
    db_type: DbType
    table_name: str = Field(min_length=1)

    def full_name(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> TableIdentifier:
        db_type = data.get("db_type")
        subclass_map: dict[str, type[TableIdentifier]] = {
            DbType.POSTGRES: PostgresTable,
            DbType.MYSQL: MySQLTable,
            DbType.BIGQUERY: BigQueryTable,
        }
        subclass = subclass_map.get(db_type)
        if subclass is None:
            raise ValueError(f"Unknown db_type: {db_type}")
        return subclass(**data)


class PostgresTable(TableIdentifier):
    db_type: DbType = DbType.POSTGRES
    schema_name: str = Field(min_length=1)

    def full_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"


class MySQLTable(TableIdentifier):
    db_type: DbType = DbType.MYSQL
    database: str = Field(min_length=1)

    def full_name(self) -> str:
        return f"{self.database}.{self.table_name}"


class BigQueryTable(TableIdentifier):
    db_type: DbType = DbType.BIGQUERY
    project: str = Field(min_length=1)
    dataset: str = Field(min_length=1)

    def full_name(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table_name}"
