# db_logic/management_queries.py
from . import _core
import logging
import os
import time
import json
import sqlite3
from typing import Dict, List

logger = logging.getLogger('discord_bot_database')

# --- THIS DICTIONARY NEEDS TO BE HERE ---
DB_NAMES_MAP = {
    "economy": "economy.db", "users": "economy.db", "transactions": "economy.db",
    "guild_settings": "economy.db", "rates": "rates.db", "default_rates": "rates.db",
    "channel_rates": "rates.db", "restricted_roles": "restricted_roles.db",
    "tasks": "tasks.db", "contact_info": "contact_info.db"
}

# --- Synchronous Functions ---
def _ping_db_sync(conn) -> float:
    start_time = time.time()
    conn.execute("SELECT 1").fetchone()
    end_time = time.time()
    return (end_time - start_time) * 1000

def _get_assignment_format_sync(conn, guild_id: int):
    cursor = conn.cursor()
    cursor.execute("SELECT assignment_format FROM guild_settings WHERE guild_id = ?", (guild_id,))
    return cursor.fetchone()

# --- Public Async Functions ---
async def get_all_db_paths_for_guild(guild_id: int, guild_name_for_path: str | None = None) -> List[str]:
    if guild_name_for_path is None:
        guild_dirs = [d for d in os.listdir(_core.GUILD_DATA_DIR) if d.endswith(f"_{guild_id}")]
        if not guild_dirs: return []
        guild_dir = os.path.join(_core.GUILD_DATA_DIR, guild_dirs[0])
    else:
        guild_dir = _core._get_guild_data_dir_path(guild_id, guild_name_for_path)
    if not os.path.isdir(guild_dir): return []
    return [os.path.join(guild_dir, f) for f in os.listdir(guild_dir) if f.endswith('.db')]

async def ping_db(guild_id: int, guild_name_for_path: str, db_type: str = "economy") -> float:
    # This now works because DB_NAMES_MAP is defined above
    db_name = DB_NAMES_MAP.get(db_type, "economy.db")
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, db_name, guild_name_for_path)
        return await _core._run_in_executor(lambda: _ping_db_sync(conn))
    except Exception as e:
        logger.error(f"Error pinging {db_type} database for guild {guild_id}: {e}", exc_info=True)
        return -1.0
    finally:
        if conn: await _core._release_db_async(guild_id, db_name, guild_name_for_path, conn)

async def clear_all(guild_id: int, guild_name_for_path: str) -> bool:
    """
    Safely closes all database connections for a guild and then deletes the files.
    This is the "DANGEROUS" option that wipes everything.
    """
    db_files = await get_all_db_paths_for_guild(guild_id, guild_name_for_path)
    if not db_files:
        logger.warning(f"clear_all called for GID {guild_id}, but no DB files were found.")
        return True

    try:
        for db_path in db_files:
            if db_path in _core._connection_pools:
                pool_lock = _core._connection_pool_locks.get(db_path)
                if pool_lock:
                    with pool_lock:
                        pool = _core._connection_pools.get(db_path, [])
                        for conn in pool:
                            try:
                                conn.close()
                            except sqlite3.Error:
                                pass
                        
                        del _core._connection_pools[db_path]
                        del _core._connection_pool_locks[db_path]
                        logger.info(f"Closed and removed connection pool for {db_path}.")

            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Successfully deleted database file: {db_path}")

        _core._invalidate_cache(guild_id, guild_name_for_path)
        logger.info(f"Cleared all database files and connection pools for guild {guild_id}.")
        return True
    except Exception as e:
        logger.error(f"Error in robust clear_all for GID {guild_id}: {e}", exc_info=True)
        return False

async def clear_all_transactions(guild_id: int, guild_name_for_path: str) -> bool:
    """Deletes all transactions and resets all user balances to zero."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        with conn:
            conn.execute("DELETE FROM transactions;")
            conn.execute("UPDATE users SET balance = 0.0;")
        _core._invalidate_cache(guild_id, guild_name_for_path)
        logger.info(f"Cleared all transactions and reset balances for guild {guild_id}.")
        return True
    except Exception as e:
        logger.error(f"Error in clear_all_transactions for GID {guild_id}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def clear_user_economy_data(guild_id: int, guild_name_for_path: str, user_id: int) -> bool:
    """Deletes a user's transactions and resets their balance, keeping their registration info."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        with conn:
            conn.execute("DELETE FROM transactions WHERE user_id = ?;", (user_id,))
            conn.execute("UPDATE users SET balance = 0.0 WHERE user_id = ?;", (user_id,))
        _core._invalidate_cache(guild_id, guild_name_for_path)
        logger.info(f"Cleared economy data for user {user_id} in guild {guild_id}.")
        return True
    except Exception as e:
        logger.error(f"Error in clear_user_economy_data for UID {user_id} in GID {guild_id}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def get_enabled_formats(guild_id: int, guild_name_for_path: str) -> List[str]:
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        row = await _core._run_in_executor(lambda: _get_assignment_format_sync(conn, guild_id))
        if row and row['assignment_format']:
            try:
                formats = json.loads(row['assignment_format'])
                return formats if isinstance(formats, list) else ['channel_based']
            except (json.JSONDecodeError, TypeError):
                return [row['assignment_format']]
        return ['channel_based']
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def set_enabled_formats(guild_id: int, guild_name_for_path: str, formats: List[str]):
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        formats_json = json.dumps(formats)
        await _core._run_in_executor(lambda: conn.execute("UPDATE guild_settings SET assignment_format = ? WHERE guild_id = ?", (formats_json, guild_id)))
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)