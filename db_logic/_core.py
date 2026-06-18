# db_logic/_core.py
import sqlite3
import os
import logging
import json
import asyncio
import re
from datetime import datetime, timezone
import functools
import threading
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict
import time

logger = logging.getLogger('discord_bot_database')
GUILD_DATA_DIR = "guild_data"
os.makedirs(GUILD_DATA_DIR, exist_ok=True)

# --- Utility Functions for Batch Operations ---
def _execute_batch(conn: sqlite3.Connection, query: str, params_list: list):
    with conn: conn.executemany(query, params_list)

def _execute_transaction(conn: sqlite3.Connection, query: str, params: tuple):
    with conn: conn.execute(query, params)

# Connection pooling constants
MAX_CONNECTIONS_PER_DB = 5
CONNECTION_TIMEOUT = 10.0
CONNECTION_TTL = 300

# Cache settings
CACHE_TTL = 60
MAX_CACHE_ITEMS = 1000

# Global connection pools and caches
_connection_pools = {}
_connection_pool_locks = {}
_connection_last_used = {}

# Cache dictionaries
_task_cache, _default_rates_cache, _channel_rates_cache, _user_balance_cache, _restricted_roles_cache, _rates_cache = {}, {}, {}, {}, {}, {}

# --- Utility Functions ---
def sanitize_guild_name_for_path(name: str | None) -> str:
    if not name: return "default_guild_name"
    name = str(name)
    name = re.sub(r'[^\w\-\.]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')[:100]

def sanitize_name(name: str | None) -> str:
    if not name: return "unknown"
    sanitized = re.sub(r'[^\w\s\-\.]', '', str(name))
    sanitized = re.sub(r'[\s_]+', '_', sanitized).strip('_')
    return sanitized[:25] if sanitized else "unknown"

async def _run_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)

def _get_guild_data_dir_path(guild_id: int, guild_name_for_path: str) -> str:
    path = os.path.join(GUILD_DATA_DIR, f"{sanitize_guild_name_for_path(guild_name_for_path)}_{guild_id}")
    os.makedirs(path, exist_ok=True)
    return path

def _get_db_path(guild_id: int, db_name: str, guild_name_for_path: str) -> str:
    return os.path.join(_get_guild_data_dir_path(guild_id, guild_name_for_path), db_name)

def _get_db_connection(guild_id: int, db_name: str, guild_name_for_path: str):
    return _acquire_connection(_get_db_path(guild_id, db_name, guild_name_for_path))

async def _connect_db_async(guild_id: int, db_name: str, guild_name_for_path: str):
    return await _run_in_executor(_get_db_connection, guild_id, db_name, guild_name_for_path)

async def _release_db_async(guild_id: int, db_name: str, guild_name_for_path: str, conn: sqlite3.Connection):
    await _run_in_executor(_release_connection, _get_db_path(guild_id, db_name, guild_name_for_path), conn)

# --- Connection pooling ---
def _get_connection_pool(db_path: str):
    if db_path not in _connection_pools:
        _connection_pools[db_path] = []
        _connection_pool_locks[db_path] = threading.Lock()
    return _connection_pools[db_path], _connection_pool_locks[db_path]

def _acquire_connection(db_path: str):
    pool, lock = _get_connection_pool(db_path)
    with lock:
        current_time = time.time()
        for conn in list(pool):
            if current_time - _connection_last_used.get(conn, 0) > CONNECTION_TTL:
                try: conn.close()
                except sqlite3.Error: pass
                pool.remove(conn)
                if conn in _connection_last_used: del _connection_last_used[conn]
        
        while pool:
            conn = pool.pop()
            try:
                conn.execute("SELECT 1")
                _connection_last_used[conn] = current_time
                return conn
            except sqlite3.Error: pass
        
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=CONNECTION_TIMEOUT)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        _connection_last_used[conn] = time.time()
        return conn

def _release_connection(db_path: str, conn: sqlite3.Connection):
    pool, lock = _get_connection_pool(db_path)
    with lock:
        if len(pool) < MAX_CONNECTIONS_PER_DB:
            _connection_last_used[conn] = time.time()
            pool.append(conn)
        else:
            try: conn.close()
            except sqlite3.Error: pass
            if conn in _connection_last_used: del _connection_last_used[conn]

# --- Cache management ---
def _get_cache_key(guild_id: int, guild_name_for_path: str, *args):
    return (guild_id, guild_name_for_path) + args

def _is_cache_valid(cache_entry):
    return cache_entry and time.time() - cache_entry.get("timestamp", 0) < CACHE_TTL

def _update_cache(cache_dict, key, data):
    if len(cache_dict) >= MAX_CACHE_ITEMS:
        oldest_key = min(cache_dict.keys(), key=lambda k: cache_dict[k].get("timestamp", 0))
        del cache_dict[oldest_key]
    cache_dict[key] = {"timestamp": time.time(), "data": data}

def _get_cached_data(cache_dict, key):
    cache_entry = cache_dict.get(key)
    return cache_entry["data"] if _is_cache_valid(cache_entry) else None

def _invalidate_cache(guild_id: int, guild_name_for_path: str | None = None):
    if guild_name_for_path:
        base_key_tuple = (guild_id, guild_name_for_path)
        for cache_dict in [_task_cache, _default_rates_cache, _restricted_roles_cache, _channel_rates_cache, _user_balance_cache, _rates_cache]:
            for k in list(cache_dict.keys()):
                if k[:2] == base_key_tuple:
                    del cache_dict[k]

# --- Synchronous Table Creation Functions ---
def _create_economy_tables_sync(conn: sqlite3.Connection, current_guild_id: int):
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, user_name TEXT NOT NULL, balance REAL DEFAULT 0.00)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, user_name TEXT NOT NULL, 
                amount REAL NOT NULL, reason TEXT, timestamp TEXT NOT NULL, 
                type TEXT NOT NULL CHECK(type IN ('add', 'less')), -- Reverted: 'payment' removed
                channel_id INTEGER, channel_name TEXT, task_name TEXT, added_by_id INTEGER, added_by_name TEXT, 
                forum_id INTEGER, post_id INTEGER, thread_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                assignment_format TEXT DEFAULT '["channel_based"]',
                forum_channel_id INTEGER
            )
        """)
        conn.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (current_guild_id,))
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_channel_id ON transactions(channel_id)")

        trans_cursor = conn.execute("PRAGMA table_info(transactions)")
        existing_cols_trans = {row[1] for row in trans_cursor.fetchall()}
        cols_to_add_trans = [('forum_id', 'INTEGER'), ('post_id', 'INTEGER'), ('thread_id', 'INTEGER')]
        for col_name, col_type in cols_to_add_trans:
            if col_name not in existing_cols_trans:
                conn.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type}")
                logger.info(f"Updated 'transactions' table with column '{col_name}' for guild {current_guild_id}.")

    logger.debug(f"Economy tables ensured for guild {current_guild_id}.")

def _create_rates_tables_sync(conn: sqlite3.Connection):
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS default_rates (id INTEGER PRIMARY KEY CHECK (id = 1), rates_json TEXT DEFAULT '{}')")
        conn.execute("INSERT OR IGNORE INTO default_rates (id, rates_json) VALUES (1, '{}')")
        conn.execute("CREATE TABLE IF NOT EXISTS channel_rates (channel_id INTEGER PRIMARY KEY, rates_json TEXT DEFAULT '{}')")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS forum_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT, context_id INTEGER NOT NULL UNIQUE,
                context_type TEXT NOT NULL, rates_json TEXT DEFAULT '{}'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_forum_rates_context ON forum_rates(context_id, context_type)")
    logger.debug("Rates tables ensured.")

def _create_restricted_roles_tables_sync(conn: sqlite3.Connection):
    with conn: 
        conn.execute("CREATE TABLE IF NOT EXISTS restricted_roles (role_id INTEGER PRIMARY KEY, role_name TEXT NOT NULL)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS command_restrictions (id INTEGER PRIMARY KEY AUTOINCREMENT, 
            role_id INTEGER NOT NULL, command_name TEXT NOT NULL, is_allowed INTEGER NOT NULL DEFAULT 0, 
            UNIQUE(role_id, command_name))
        """)
    logger.debug("Restricted roles tables ensured.")

def _create_tasks_tables_sync(conn: sqlite3.Connection):
    with conn: conn.execute("CREATE TABLE IF NOT EXISTS tasks (task_name TEXT PRIMARY KEY, rank INTEGER DEFAULT 0)")
    logger.debug("Tasks table ensured.")

def _create_contact_info_tables_sync(conn: sqlite3.Connection):
    with conn: conn.execute("CREATE TABLE IF NOT EXISTS contact_info (user_id INTEGER PRIMARY KEY, user_name TEXT, email TEXT, payment_method TEXT)")
    logger.debug("Contact info table ensured.")

# --- Connection Pool Maintenance ---
async def _cleanup_connection_pools():
    while True:
        await asyncio.sleep(60)
        try:
            current_time = time.time()
            for db_path, pool in list(_connection_pools.items()):
                lock = _connection_pool_locks.get(db_path)
                if not lock: continue
                with lock:
                    for conn in list(pool):
                        if current_time - _connection_last_used.get(conn, 0) > CONNECTION_TTL:
                            try: conn.close()
                            except sqlite3.Error: pass
                            pool.remove(conn)
                            if conn in _connection_last_used: del _connection_last_used[conn]
        except Exception as e:
            logger.error(f"Error cleaning up connection pools: {e}", exc_info=True)