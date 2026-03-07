from enum import Enum

from pydantic import BaseModel


class DbType(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    BIGQUERY = "bigquery"


class ConnectionSummary(BaseModel):
    id: str
    name: str
    db_type: DbType
