from pydantic import BaseModel, Field

from local_backend.models.common import DbType


class ConnectionParams(BaseModel):
    name: str = Field(min_length=1)
    db_type: DbType


class PostgresConnectionParams(ConnectionParams):
    db_type: DbType = DbType.POSTGRES
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    database: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class MySQLConnectionParams(ConnectionParams):
    db_type: DbType = DbType.MYSQL
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    database: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class BigQueryConnectionParams(ConnectionParams):
    db_type: DbType = DbType.BIGQUERY
    project_id: str = Field(min_length=1)
    service_account_json: str = Field(min_length=1)
