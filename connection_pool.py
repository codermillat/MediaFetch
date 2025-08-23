"""
Database Connection Pooling for MediaFetch
Provides efficient database connection management and query optimization
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import threading

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """Thread-safe database connection pool for PostgreSQL/Supabase"""

    def __init__(self,
                 min_connections: int = 2,
                 max_connections: int = 10,
                 connection_timeout: int = 30,
                 max_retries: int = 3):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_retries = max_retries

        # Connection pool
        self._pool: Optional[pool.ThreadedConnectionPool] = None
        self._lock = threading.Lock()

        # Connection health tracking
        self.connection_stats = {
            'active_connections': 0,
            'total_queries': 0,
            'failed_connections': 0,
            'connection_errors': 0
        }

        # Query performance tracking
        self.query_stats: Dict[str, List[float]] = {}

    def initialize(self, connection_string: str = None) -> bool:
        """Initialize the connection pool"""
        try:
            if connection_string is None:
                connection_string = self._build_connection_string()

            with self._lock:
                self._pool = pool.ThreadedConnectionPool(
                    minconn=self.min_connections,
                    maxconn=self.max_connections,
                    dsn=connection_string,
                    connect_timeout=self.connection_timeout
                )

            logger.info(f"Database connection pool initialized with {self.min_connections}-{self.max_connections} connections")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            return False

    def _build_connection_string(self) -> str:
        """Build connection string from environment variables"""
        required_vars = ['SUPABASE_URL']
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

        # For Supabase, construct PostgreSQL connection string
        supabase_url = os.getenv('SUPABASE_URL')
        if 'supabase.co' in supabase_url:
            # Convert Supabase URL to PostgreSQL connection string
            return f"postgresql://postgres:{os.getenv('SUPABASE_SERVICE_ROLE_KEY')}@{supabase_url.replace('https://', '').replace('/rest/v1', '')}:5432/postgres"

        return supabase_url

    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool with automatic cleanup"""
        if not self._pool:
            raise RuntimeError("Connection pool not initialized")

        connection = None
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                connection = self._pool.getconn()
                self.connection_stats['active_connections'] += 1

                # Test connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

                yield connection
                break

            except Exception as e:
                retry_count += 1
                self.connection_stats['connection_errors'] += 1
                logger.warning(f"Database connection attempt {retry_count} failed: {e}")

                if connection:
                    try:
                        self._pool.putconn(connection, close=True)
                    except:
                        pass
                    connection = None

                if retry_count >= self.max_retries:
                    logger.error(f"All {self.max_retries} connection attempts failed")
                    raise RuntimeError("Unable to establish database connection") from e

                time.sleep(0.5 * retry_count)  # Exponential backoff

            finally:
                if connection:
                    self.connection_stats['active_connections'] -= 1
                    try:
                        self._pool.putconn(connection)
                    except Exception as e:
                        logger.error(f"Error returning connection to pool: {e}")
                        try:
                            self._pool.putconn(connection, close=True)
                        except:
                            pass

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[List[Dict]]:
        """Execute a database query with connection pooling and error handling"""
        start_time = time.time()

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params or ())

                    if fetch:
                        results = cursor.fetchall()
                        self.connection_stats['total_queries'] += 1
                        return [dict(row) for row in results]
                    else:
                        conn.commit()
                        self.connection_stats['total_queries'] += 1
                        return None

        except Exception as e:
            logger.error(f"Query execution failed: {query} - {e}")
            raise
        finally:
            # Track query performance
            query_time = time.time() - start_time
            if query not in self.query_stats:
                self.query_stats[query] = []
            self.query_stats[query].append(query_time)

    def execute_transaction(self, queries: List[Dict[str, Any]]) -> bool:
        """Execute multiple queries in a single transaction"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    for query_info in queries:
                        query = query_info['query']
                        params = query_info.get('params', ())
                        cursor.execute(query, params)

                    conn.commit()
                    self.connection_stats['total_queries'] += len(queries)
                    return True

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if not self._pool:
            return {"error": "Pool not initialized"}

        return {
            **self.connection_stats,
            "pool_size": self._pool.size() if self._pool else 0,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "query_performance": {
                query: {
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times),
                    "total_executions": len(times)
                }
                for query, times in self.query_stats.items()
            }
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database connection pool"""
        try:
            # Test basic connectivity
            result = self.execute_query("SELECT 1 as health_check")
            if result and result[0]['health_check'] == 1:
                pool_stats = self.get_pool_stats()
                return {
                    "healthy": True,
                    "status": "Connection pool is healthy",
                    "pool_stats": pool_stats
                }
            else:
                return {
                    "healthy": False,
                    "status": "Database query failed"
                }

        except Exception as e:
            return {
                "healthy": False,
                "status": f"Connection pool health check failed: {e}"
            }

    def close(self):
        """Close the connection pool"""
        if self._pool:
            with self._lock:
                self._pool.closeall()
                self._pool = None
                logger.info("Database connection pool closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global connection pool instance
_db_pool: Optional[DatabaseConnectionPool] = None


def get_db_pool() -> DatabaseConnectionPool:
    """Get the global database connection pool instance"""
    global _db_pool

    if _db_pool is None:
        _db_pool = DatabaseConnectionPool()
        if not _db_pool.initialize():
            raise RuntimeError("Failed to initialize database connection pool")

    return _db_pool


def init_db_pool():
    """Initialize the global database connection pool"""
    pool = get_db_pool()
    logger.info("Global database connection pool initialized")


def close_db_pool():
    """Close the global database connection pool"""
    global _db_pool

    if _db_pool:
        _db_pool.close()
        _db_pool = None
        logger.info("Global database connection pool closed")
