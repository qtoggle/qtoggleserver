
import datetime
import logging
import re

from typing import Any, AsyncContextManager, Dict, Iterable, List, Optional, Set, Tuple

import asyncpg.pool

from qtoggleserver.persist import BaseDriver
from qtoggleserver.persist.typing import Id, Record
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)

DEFAULT_DB = 'qtoggleserver'
POOL_MIN_CONNECTIONS = 2
POOL_MAX_CONNECTIONS = 4
POOL_MAX_QUERIES = 256

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
        logger.debug('using %s:%s/%s', host, port, db)

        conn_details = {
            'host': host,
            'port': port,
            'dbname': db
        }

        if username:
            conn_details['user'] = username
        if password:
            conn_details['password'] = password

        self._conn_details = {
            'user': username,
            'password': password,
            'database': db,
            'host': host,
            'port': port
        }

        self._conn_pool: Optional[asyncpg.pool.Pool] = None
        self._existing_tables: Optional[Set[str]] = None

    async def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        sort: List[Tuple[str, bool]],
        limit: Optional[int]
    ) -> Iterable[Record]:

        await self._ensure_table_exists(collection)

        params = []
        if fields:
            select_clause = self._fields_to_select_clause(fields, params)

        else:
            select_clause = 'id, content'

        query = f'SELECT {select_clause} FROM {collection}'

        where_clause = self._filt_to_where_clause(self._filt_to_db(filt), params)
        if where_clause:
            query += f' WHERE {where_clause}'

        if sort:
            order_by_clause = self._fields_to_order_by_clause(sort, params)
            query += f' ORDER BY {order_by_clause}'

        if limit is not None:
            query += f' LIMIT ${len(params) + 1}'
            params.append(limit)

        results = await self._execute_query(query, params)

        return self._query_gen_wrapper(results, fields)

    async def insert(self, collection: str, record: Record) -> Id:
        await self._ensure_table_exists(collection)

        db_record = self._record_to_db(record)
        id_ = db_record.pop('id', None)

        if id_ is not None:
            statement = f'INSERT INTO {collection}(id, content) VALUES($1, $2) RETURNING id'
            params = [id_, db_record]

        else:
            statement = f'INSERT INTO {collection}(content) VALUES($1) RETURNING id'
            params = [db_record]

        _, result_rows = await self._execute_statement(statement, params, has_result_rows=True)

        return result_rows[0][0]

    async def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        await self._ensure_table_exists(collection)

        params = []
        statement = f'UPDATE {collection}'

        db_record_part = self._record_to_db(record_part)
        update_clause = self._record_to_update_clause(db_record_part, params)
        statement += f' SET {update_clause}'

        where_clause = self._filt_to_where_clause(self._filt_to_db(filt), params)
        if where_clause:
            statement += f' WHERE {where_clause}'

        status_msg, _ = await self._execute_statement(statement, params)

        count = int(status_msg.split()[1])  # Assuming status_msg has format "UPDATE ${count}"

        return count

    async def replace(self, collection: str, id_: Id, record: Record) -> bool:
        await self._ensure_table_exists(collection)

        db_record = self._record_to_db(record)
        statement = f'UPDATE {collection} SET content = $1 WHERE id = $2'
        params = [db_record, id_]

        status_msg, _ = await self._execute_statement(statement, params)

        count = int(status_msg.split()[1])  # Assuming status_msg has format "UPDATE ${count}"

        return count > 0

    async def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        await self._ensure_table_exists(collection)

        params = []
        statement = f'DELETE FROM {collection}'

        where_clause = self._filt_to_where_clause(self._filt_to_db(filt), params)
        if where_clause:
            statement += f' WHERE {where_clause}'

        status_msg, _ = await self._execute_statement(statement, params)

        count = int(status_msg.split()[1])  # Assuming status_msg has format "DELETE ${count}"

        return count

    async def ensure_index(self, collection: str, index: List[Tuple[str, bool]]) -> None:
        await self._ensure_table_exists(collection)

        field_names = [i[0] for i in index]
        field_names_str = '_'.join(field_names)
        index_name = f'{collection}_{field_names_str}'

        params = []
        index_statement = self._index_to_index_clause(index, params)
        statement = f'CREATE INDEX IF NOT EXISTS {index_name} ON {collection}({index_statement})'

        await self._execute_statement(statement, params)

    async def cleanup(self) -> None:
        logger.debug('disconnecting client')

        if self._conn_pool:
            await self._conn_pool.close()
            self._conn_pool = None

    def is_history_supported(self) -> bool:
        return True

    async def _acquire_connection(self) -> AsyncContextManager[asyncpg.Connection]:
        if self._conn_pool is None:
            logger.debug('creating connection pool')
            self._conn_pool = await asyncpg.create_pool(
                min_size=POOL_MIN_CONNECTIONS,
                max_size=POOL_MAX_CONNECTIONS,
                max_queries=POOL_MAX_QUERIES,
                init=self._init_connection,
                **self._conn_details
            )

        return self._conn_pool.acquire()

    async def _init_connection(self, conn: asyncpg.Connection) -> None:
        # Install JSON converter
        await conn.set_type_codec(
            'jsonb',
            encoder=json_utils.dumps,
            decoder=json_utils.loads,
            schema='pg_catalog',
            format='text'
        )

    async def _ensure_table_exists(self, table_name: str) -> None:
        if self._existing_tables is None:
            self._existing_tables = await self._get_existing_table_names()

        if table_name in self._existing_tables:
            return

        statement = f'CREATE SEQUENCE {table_name}_id_seq'
        await self._execute_statement(statement)

        id_data_type = f"TEXT NOT NULL DEFAULT NEXTVAL('{table_name}_id_seq') PRIMARY KEY"
        statement = f'CREATE TABLE {table_name}(id {id_data_type}, content JSONB)'
        await self._execute_statement(statement)

        self._existing_tables.add(table_name)

    async def _get_existing_table_names(self) -> Set[str]:
        query = (
            "SELECT table_name "
            "FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' AND table_schema = 'public'"
        )

        results = await self._execute_query(query)

        return set(r[0] for r in results)

    async def _execute_query(self, query: str, params: Iterable[Any] = None) -> Iterable[tuple]:
        async with await self._acquire_connection() as conn:
            async with conn.transaction():
                return [row async for row in conn.cursor(query, *(params or []))]

    async def _execute_statement(
        self,
        statement: str,
        params: Iterable[Any] = None,
        has_result_rows: bool = False
    ) -> Tuple[str, List[tuple]]:
        async with await self._acquire_connection() as conn:
            stmt = await conn.prepare(statement)

            async with conn.transaction():
                rows = await stmt.fetch(*(params or []))
                if has_result_rows:
                    return stmt.get_statusmsg(), rows

                else:
                    return stmt.get_statusmsg(), []

    @staticmethod
    def _fields_to_select_clause(fields: List[str], params: List[Any]) -> str:
        select_clause = []

        for field in fields:
            if field == 'id':
                select_clause.append('id')

            else:
                select_clause.append(f'content->${len(params) + 1}')
                params.append(field)

        select_clause = ', '.join(select_clause)

        return select_clause

    @staticmethod
    def _fields_to_order_by_clause(fields: List[Tuple[str, bool]], params: List[Any]) -> str:
        order_by_clause = []

        for field, desc in fields:
            if field == 'id':
                clause = "SUBSTRING(id FROM '([0-9]+)')::int"

            else:
                clause = f'content->${len(params) + 1}'
                params.append(field)

            clause = f"{clause} {'DESC' if desc else 'ASC'}"
            order_by_clause.append(clause)

        order_by_clause = ', '.join(order_by_clause)

        return order_by_clause

    @staticmethod
    def _filt_to_where_clause(filt: Dict[str, Any], params: List[Any]) -> str:
        where_clause = []

        for key, value in filt.items():
            if isinstance(value, dict):  # filter with operators
                ops_values = [(FILTER_OP_MAPPING[k], v) for k, v in value.items()]

            else:
                ops_values = [('=', value)]

            if key == 'id':
                for o, v in ops_values:
                    if o == 'in':
                        placeholder = ', '.join(f'${len(params) + 1 + i}' for i, _ in enumerate(v))
                        placeholder = f'({placeholder})'
                        params += v

                    else:
                        placeholder = f'${len(params) + 1}'
                        params.append(v)

                    condition = f'{key} {o} {placeholder}'
                    where_clause.append(condition)

            else:
                for o, v in ops_values:
                    if o == 'in':
                        placeholder = ', '.join(f'${len(params) + 1 + i}' for i, _ in enumerate(v))
                        placeholder = f'({placeholder})'
                        params += v

                    else:
                        placeholder = f'${len(params) + 1}'
                        params.append(v)

                    condition = f"content->'{key}' {o} {placeholder}"
                    where_clause.append(condition)

        where_clause = ' AND '.join(where_clause)

        return where_clause

    @staticmethod
    def _record_to_update_clause(record: Record, params: List[Any]) -> str:
        update_clause = []

        id_ = record.pop('id', None)
        if id_ is not None:
            update_clause.append(f'id = ${len(params) + 1}')
            params.append(id_)

        if record:
            update_clause.append(f'content = content || ${len(params) + 1}')
            params.append(record)

        update_clause = ', '.join(update_clause)

        return update_clause

    @staticmethod
    def _index_to_index_clause(index: List[Tuple[str, bool]], params: List[Any]) -> str:
        index_clause = []

        # We can't use prepared statements with CREATE INDEX, so we need to build our query without arguments
        for field, _ in index:
            field = re.sub(r'[^a-zA-Z0-9_]', '', field)
            index_clause.append(f"(content->'${field}')")

        index_clause = ', '.join(index_clause)

        return index_clause

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
