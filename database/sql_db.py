"""Database client."""

from typing import List, Optional

from pandas import DataFrame
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.engine import CursorResult
from sqlalchemy.engine.result import Result
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from log import LOGGER

metadata_obj = MetaData()


class Database:
    """Database client."""

    def __init__(self, uri: str, db_name: str, args: dict):
        self.db = create_engine(f"{uri}/{db_name}", connect_args=args, echo=False)

    def _table(self, table_name: str) -> Table:
        """
        Build database table object.

        :param str table_name: Name of database table to fetch

        :returns: Table
        """
        return Table(table_name, MetaData, autoload=True)

    def execute_queries(self, queries: dict) -> dict:
        """
        Execute collection of SQL analytics.

        :param dict queries: Map of query names -> SQL analytics.

        :returns: dict
        """
        try:
            results = {}
            with self.db.begin() as conn:
                for k, v in queries.items():
                    query_result = conn.execute(v)
                    results[k] = f"{query_result.rowcount} rows affected."
                return results
        except SQLAlchemyError as e:
            LOGGER.error(f"SQLAlchemyError while executing queries `{','.join(queries.keys())}`: {e}")
        except Exception as e:
            LOGGER.error(f"Unexpected exception while executing queries `{','.join(queries.keys())}`: {e}")

    def execute_query(self, query: str) -> Optional[CursorResult]:
        """
        Execute single SQL query.

        :param str query: SQL query to run against database.

        :returns: Optional[CursorResult]
        """
        try:
            with self.db.begin() as conn:
                return conn.execute(text(query))
        except SQLAlchemyError as e:
            LOGGER.error(f"Failed to execute SQL query {query}: {e}")

    def execute_query_from_file(self, sql_file: str) -> Optional[CursorResult]:
        """
        Execute single SQL query.

        :param str sql_file: Filepath of SQL query to run.

        :returns: Optional[CursorResult]
        """
        try:
            with self.db.begin() as conn:
                with open(sql_file, "r", encoding="utf-8") as query:
                    return conn.execute(text(query))
        except SQLAlchemyError as e:
            LOGGER.error(f"SQLAlchemyError while executing SQL `{sql_file}`: {e}")
            return f"Failed to execute SQL `{sql_file}`: {e}"
        except Exception as e:
            LOGGER.error(f"Unexpected exception while executing SQL `{sql_file}`: {e}")
            return f"Failed to execute SQL `{sql_file}`: {e}"

    def insert_records(self, rows: List[dict], table_name: str, replace=False) -> Result:
        """
        Insert rows into SQL table.

        :param List[dict] rows: List of dictionaries to insert where keys are columns.
        :param str table_name: Name of database table to fetch.
        :param bool replace: Flag to truncate table prior to insert.

        :returns: Result
        """
        try:
            if replace:
                self.db.execute(f"TRUNCATE TABLE {table_name}")
            table = self._table(table_name)
            return self.db.execute(table.insert(), rows)
        except IntegrityError as e:
            LOGGER.error(f"IntegrityError error while inserting records into table `{table_name}`: {e}")
        except SQLAlchemyError as e:
            LOGGER.error(f"SQLAlchemyError while inserting records into table `{table_name}`: {e}")
        except Exception as e:
            LOGGER.error(f"Unexpected error while inserting records into table `{table_name}`: {e}")

    def insert_dataframe(self, df: DataFrame, table_name: str, action="append") -> DataFrame:
        """
        Insert Pandas DataFrame into SQL table.

        :param DataFrame df: Tabular data to insert into SQL table.
        :param str table_name: Name of database table to insert into.
        :param str action: Method of dealing with duplicate rows.

        :returns: DataFrame
        """
        df.to_sql(table_name, self.db, if_exists=action)
        LOGGER.info(f"Updated {len(df)} rows via {action} into `{table_name}`.")
        return df
