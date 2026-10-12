"""PostgreSQL cache with atomic counters across serverless instances."""

import base64
import pickle

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.db import DatabaseCache
from django.db import connections, router, transaction
from django.utils import timezone


class AtomicDatabaseCache(DatabaseCache):
    def _cull(self, db, cursor, now, num):
        # Never evict an unexpired throttle counter under ordinary cache pressure.
        table = connections[db].ops.quote_name(self._table)
        cursor.execute(f"DELETE FROM {table} WHERE expires < %s", [now])

    def _base_set(self, mode, key, value, timeout=DEFAULT_TIMEOUT):
        database = router.db_for_write(self.cache_model_class)
        with transaction.atomic(using=database):
            with connections[database].cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [key])
            return super()._base_set(mode, key, value, timeout)

    def incr(self, key, delta=1, version=None):
        key = self.make_and_validate_key(key, version=version)
        database = router.db_for_write(self.cache_model_class)
        connection = connections[database]
        table = connection.ops.quote_name(self._table)
        with transaction.atomic(using=database), connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [key])
            cursor.execute(
                f"SELECT value, expires FROM {table} WHERE cache_key = %s FOR UPDATE",
                [key],
            )
            row = cursor.fetchone()
            if row is None or row[1] < timezone.now():
                raise ValueError("Cache counter is missing or expired.")
            value = pickle.loads(base64.b64decode(row[0])) + delta
            encoded = base64.b64encode(pickle.dumps(value, self.pickle_protocol)).decode("ascii")
            # Preserve the original expiry: requests cannot extend a throttle window.
            cursor.execute(f"UPDATE {table} SET value = %s WHERE cache_key = %s", [encoded, key])
            return value
