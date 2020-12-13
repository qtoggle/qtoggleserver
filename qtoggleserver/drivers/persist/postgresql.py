
import datetime
import logging
import re

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import psycopg2.extensions
import psycopg2.extras

from qtoggleserver.persist import BaseDriver
from qtoggleserver.persist.typing import Id, Record
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)

DEFAULT_DB = 'qtoggleserver'

FILTER_OP_MAPPING = {
    'gt': '>',
    'ge': '>=',
    'lt': '<',
    'le': '<=',
    'in': 'in'
}

D_FMT = '__{:04d}-{:02d}-{:02d}T'
D_FMT_LEN = 13
D_REGEX = re.compile(r'^__(\d{4})-(\d{2})-(\d{2})T$')

DT_FMT = '__{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:06d}Z'
DT_FMT_LEN = 29
DT_REGEX = re.compile(r'^__(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{6})Z$')


class PostgreSQLDriver(BaseDriver):
    def __init__(
        self,
        host: str = '127.0.0.1',
        port: str = 5432,
        db: str = DEFAULT_DB,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ) -> None:

        logger.debug('connecting to %s:%s/%s', host, port, db)

        conn_details = {
            'host': host,
            'port': port,
            'dbname': db
        }

        if username:
            conn_details['user'] = username
        if password:
            conn_details['password'] = password

        conn_str = ' '.join(f'{k}=\'{v}\'' for (k, v) in conn_details.items())

        self._conn = psycopg2.connect(conn_str)
        self._existing_tables: Set[str] = self._get_existing_table_names()

    def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        sort: List[Tuple[str, bool]],
        limit: Optional[int]
    ) -> Iterable[Record]:

        self._ensure_table_exists(collection)

        params = []
        if fields:
            select_clause, p = self._fields_to_select_clause(fields)
            params += p

        else:
            select_clause = 'id, content'

        query = f'SELECT {select_clause} FROM {collection}'

        where_clause, p = self._filt_to_where_clause(self._filt_to_db(filt))
        params += p
        if where_clause:
            query += f' WHERE {where_clause}'

        if sort:
            order_by_clause, p = self._fields_to_order_by_clause(sort)
            params += p
            query += f' ORDER BY {order_by_clause}'

        if limit is not None:
            query += ' LIMIT %s'
            params.append(limit)

        results = self._execute_query(query, params)

        return self._query_gen_wrapper(results, fields)

    def insert(self, collection: str, record: Record) -> Id:
        self._ensure_table_exists(collection)

        db_record = self._record_to_db(record)
        id_ = db_record.pop('id', None)

        if id_ is not None:
            statement = f'INSERT INTO {collection}(id, content) VALUES(%s, %s) RETURNING id'
            params = [id_, db_record]

        else:
            statement = f'INSERT INTO {collection}(content) VALUES(%s) RETURNING id'
            params = [db_record]

        count, result_rows = self._execute_statement(statement, params, has_result_rows=True)

        return result_rows[0][0]

    def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        self._ensure_table_exists(collection)

        params = []
        statement = f'UPDATE {collection}'

        db_record_part = self._record_to_db(record_part)
        update_clause, p = self._record_to_update_clause(db_record_part)
        params += p
        statement += f' SET {update_clause}'

        where_clause, p = self._filt_to_where_clause(self._filt_to_db(filt))
        params += p
        if where_clause:
            statement += f' WHERE {where_clause}'

        count, _ = self._execute_statement(statement, params)

        return count

    def replace(self, collection: str, id_: Id, record: Record) -> bool:
        self._ensure_table_exists(collection)

        db_record = self._record_to_db(record)
        statement = f'UPDATE {collection} SET content = %s WHERE id = %s'
        params = [db_record, id_]

        count, _ = self._execute_statement(statement, params)

        return count > 0

    def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        self._ensure_table_exists(collection)

        params = []
        statement = f'DELETE FROM {collection}'

        where_clause, p = self._filt_to_where_clause(self._filt_to_db(filt))
        params += p
        if where_clause:
            statement += f' WHERE {where_clause}'

        count, _ = self._execute_statement(statement, params)

        return count

    def ensure_index(self, collection: str, index: List[Tuple[str, bool]]) -> None:
        self._ensure_table_exists(collection)

        field_names = [i[0] for i in index]
        field_names_str = '_'.join(field_names)
        index_name = f'{collection}_{field_names_str}'

        index_statement, params = self._index_to_index_clause(index)
        statement = f'CREATE INDEX IF NOT EXISTS {index_name} ON {collection}({index_statement})'

        self._execute_statement(statement, params)

    async def cleanup(self) -> None:
        logger.debug('disconnecting client')

        self._conn.close()

    def is_history_supported(self) -> bool:
        return True

    def get_connection(self) -> Any:
        return self._conn

    def _ensure_table_exists(self, table_name: str) -> None:
        if table_name in self._existing_tables:
            return

        statement = f'CREATE SEQUENCE {table_name}_id_seq'
        self._execute_statement(statement)

        id_data_type = f"TEXT NOT NULL DEFAULT NEXTVAL('{table_name}_id_seq') PRIMARY KEY"
        statement = f'CREATE TABLE {table_name}(id {id_data_type}, content JSONB)'
        self._execute_statement(statement)

        self._existing_tables.add(table_name)

    def _get_existing_table_names(self) -> Set[str]:
        query = (
            "SELECT table_name "
            "FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' AND table_schema = 'public'"
        )

        results = self._execute_query(query)

        return set(r[0] for r in results)

    def _execute_query(self, query: str, params: Iterable[Any] = None) -> Iterable[tuple]:
        with self._conn:
            cur = self._conn.cursor()
            cur.execute(query, params)
            return cur

    def _execute_statement(
        self,
        statement: str,
        params: Iterable[Any] = None,
        has_result_rows: bool = False
    ) -> Tuple[int, List[tuple]]:
        with self._conn:
            cur = self._conn.cursor()
            cur.execute(statement, params)
            if has_result_rows:
                return cur.rowcount, cur.fetchall()

            else:
                return cur.rowcount, []

    @staticmethod
    def _fields_to_select_clause(fields: List[str]) -> Tuple[str, Iterable[Any]]:
        select_clause = []
        params = []

        for field in fields:
            if field == 'id':
                select_clause.append('id')

            else:
                select_clause.append("content->%s")
                params.append(field)

        select_clause = ', '.join(select_clause)

        return select_clause, params

    @staticmethod
    def _fields_to_order_by_clause(fields: List[Tuple[str, bool]]) -> Tuple[str, Iterable[Any]]:
        order_by_clause = []
        params = []

        for field, desc in fields:
            if field == 'id':
                clause = "SUBSTRING(id FROM '([0-9]+)')::int"

            else:
                clause = "content->%s"
                params.append(field)

            clause = f"{clause} {'DESC' if desc else 'ASC'}"
            order_by_clause.append(clause)

        order_by_clause = ', '.join(order_by_clause)

        return order_by_clause, params

    @staticmethod
    def _filt_to_where_clause(filt: Dict[str, Any]) -> Tuple[str, Iterable[Any]]:
        where_clause = []
        params = []

        for key, value in filt.items():
            if isinstance(value, dict):  # filter with operators
                ops_values = [(FILTER_OP_MAPPING[k], v) for k, v in value.items()]

            else:
                ops_values = [('=', value)]

            if key == 'id':
                for o, v in ops_values:
                    if o == 'in':
                        placeholder = ', '.join('%s' for _ in v)
                        placeholder = f'({placeholder})'
                        params += v

                    else:
                        placeholder = '%s'
                        params.append(v)

                    condition = f"{key} {o} {placeholder}"
                    where_clause.append(condition)

            else:
                for o, v in ops_values:
                    if o == 'in':
                        placeholder = ', '.join('%s' for _ in v)
                        placeholder = f'({placeholder})'
                        params += (json_utils.dumps(vv) for vv in v)

                    else:
                        placeholder = '%s'
                        params.append(json_utils.dumps(v))

                    condition = f"content->'{key}' {o} {placeholder}"
                    where_clause.append(condition)

        where_clause = ' AND '.join(where_clause)

        return where_clause, params

    @staticmethod
    def _record_to_update_clause(record: Record) -> Tuple[str, Iterable[Any]]:
        update_clause = []
        params = []

        id_ = record.pop('id', None)
        if id_ is not None:
            update_clause.append('id = %s')
            params.append(id_)

        if record:
            update_clause.append('content = content || %s')
            params.append(record)

        update_clause = ', '.join(update_clause)

        return update_clause, params

    @staticmethod
    def _index_to_index_clause(index: List[Tuple[str, bool]]) -> Tuple[str, Iterable[Any]]:
        index_clause = []
        params = []

        for field, _ in index:
            index_clause.append('(content->%s)')
            params.append(field)

        index_clause = ', '.join(index_clause)

        return index_clause, params

    def _query_gen_wrapper(self, results: Iterable[Tuple[Any]], fields: Optional[List[str]]) -> Iterable[Record]:
        if fields:
            for result in results:
                db_record = {fields[i]: r for i, r in enumerate(result)}
                yield self._record_from_db(db_record)

        else:
            for result in results:
                id_, db_record = result
                db_record['id'] = id_
                yield self._record_from_db(db_record)

    def _filt_to_db(self, filt: Dict[str, Any]) -> Dict[str, Any]:
        db_filt = {}
        for key, value in filt.items():
            if isinstance(value, dict):  # filter with operators
                value = {k: self.value_to_db(v) for k, v in value.items()}

            else:
                value = self.value_to_db(value)

            db_filt[key] = value

        return db_filt

    def _record_to_db(self, record: Record) -> Record:
        return {k: self.value_to_db(v) for k, v in record.items()}

    def _record_from_db(self, record: Record) -> Record:
        return {k: self.value_from_db(v) for k, v in record.items()}

    def value_to_db(self, value: Any) -> Any:
        if isinstance(value, datetime.datetime):
            return self.datetime_to_str(value)

        if isinstance(value, datetime.date):
            return self.date_to_str(value)

        return value

    def value_from_db(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.str_to_datetime(value) or self.str_to_date(value) or value

        return value

    @staticmethod
    def datetime_to_str(dt: datetime.datetime) -> str:
        return DT_FMT.format(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond)

    @staticmethod
    def str_to_datetime(s: str) -> Optional[datetime.datetime]:
        if len(s) != DT_FMT_LEN:
            return

        m = DT_REGEX.match(s)
        if m is None:
            return

        return datetime.datetime(*(int(g) for g in m.groups()))

    @staticmethod
    def date_to_str(dt: datetime.date) -> str:
        return D_FMT.format(dt.year, dt.month, dt.day)

    @staticmethod
    def str_to_date(s: str) -> Optional[datetime.date]:
        if len(s) != D_FMT_LEN:
            return

        m = D_REGEX.match(s)
        if m is None:
            return

        return datetime.date(*(int(g) for g in m.groups()))


psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)
