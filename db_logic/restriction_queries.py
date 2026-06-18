# db_logic/restriction_queries.py
from . import _core
import logging

logger = logging.getLogger('discord_bot_database')

# --- Synchronous Functions ---

def _get_restricted_roles_sync(conn) -> list[int]:
    """Get list of restricted role IDs."""
    cursor = conn.cursor()
    cursor.execute("SELECT role_id FROM restricted_roles")
    return [row['role_id'] for row in cursor.fetchall() if row and row['role_id'] is not None]

def _get_restricted_roles_with_names_sync(conn) -> list[dict]:
    """Get list of restricted roles with their names."""
    cursor = conn.cursor()
    cursor.execute("SELECT role_id, role_name FROM restricted_roles")
    return [dict(row) for row in cursor.fetchall()]

def _add_restricted_role_sync(conn, role_id: int, role_name: str):
    """Add a role to the restricted list."""
    with conn: conn.execute("INSERT OR IGNORE INTO restricted_roles (role_id, role_name) VALUES (?, ?)", (role_id, role_name))

def _remove_restricted_role_sync(conn, role_id: int):
    """Remove a role from the restricted list."""
    with conn: conn.execute("DELETE FROM restricted_roles WHERE role_id = ?", (role_id,))

def _get_command_restrictions_for_role_sync(conn, role_id: int) -> list[dict]:
    """Get all command restrictions for a role."""
    cursor = conn.cursor()
    cursor.execute("SELECT command_name, is_allowed FROM command_restrictions WHERE role_id = ?", (role_id,))
    return [dict(row) for row in cursor.fetchall()]

def _set_command_restriction_sync(conn, role_id: int, command_name: str, is_allowed: bool):
    """Set or update a command restriction for a role."""
    with conn: 
        conn.execute("INSERT OR REPLACE INTO command_restrictions (role_id, command_name, is_allowed) VALUES (?, ?, ?)", 
                    (role_id, command_name, 1 if is_allowed else 0))

def _remove_command_restriction_sync(conn, role_id: int, command_name: str):
    """Remove a command restriction for a role."""
    with conn: 
        conn.execute("DELETE FROM command_restrictions WHERE role_id = ? AND command_name = ?", 
                    (role_id, command_name))

def _get_all_command_restrictions_sync(conn) -> list[dict]:
    """Get all command restrictions for all roles."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cr.role_id, r.role_name, cr.command_name, cr.is_allowed 
        FROM command_restrictions cr
        LEFT JOIN restricted_roles r ON cr.role_id = r.role_id
    """)
    return [dict(row) for row in cursor.fetchall()]

def _is_command_allowed_for_role_sync(conn, role_id: int, command_name: str) -> bool:
    """Check if a command is specifically allowed for a role."""
    cursor = conn.cursor()
    cursor.execute("SELECT is_allowed FROM command_restrictions WHERE role_id = ? AND command_name = ?", 
                  (role_id, command_name))
    row = cursor.fetchone()
    return bool(row and row['is_allowed'] == 1)

# --- Public Async Functions ---

async def get_restricted_roles(guild_id: int, guild_name_for_path: str) -> list[int]:
    """Get list of restricted role IDs with caching."""
    cache_key = _core._get_cache_key(guild_id, guild_name_for_path)
    cached_roles = _core._get_cached_data(_core._restricted_roles_cache, cache_key)
    if cached_roles is not None:
        return cached_roles
    
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        roles = await _core._run_in_executor(lambda: _get_restricted_roles_sync(conn))
        _core._update_cache(_core._restricted_roles_cache, cache_key, roles)
        return roles
    except Exception as e:
        logger.error(f"Error in get_restricted_roles GID {guild_id}: {e}", exc_info=True)
        return []
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def get_restricted_roles_with_names(guild_id: int, guild_name_for_path: str) -> list[dict]:
    """Get list of restricted roles with their names."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_restricted_roles_with_names_sync(conn))
    except Exception as e:
        logger.error(f"Error in get_restricted_roles_with_names GID {guild_id}: {e}", exc_info=True)
        return []
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def add_restricted_role(guild_id: int, guild_name_for_path: str, role_id: int, role_name: str):
    """Add a role to the restricted list with cache invalidation."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _add_restricted_role_sync(conn, role_id, role_name))
        cache_key = _core._get_cache_key(guild_id, guild_name_for_path)
        if cache_key in _core._restricted_roles_cache:
            del _core._restricted_roles_cache[cache_key]
    except Exception as e:
        logger.error(f"Error in add_restricted_role GID {guild_id} RID {role_id}: {e}", exc_info=True)
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def remove_restricted_role(guild_id: int, guild_name_for_path: str, role_id: int):
    """Remove a role from the restricted list with cache invalidation."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _remove_restricted_role_sync(conn, role_id))
        cache_key = _core._get_cache_key(guild_id, guild_name_for_path)
        if cache_key in _core._restricted_roles_cache:
            del _core._restricted_roles_cache[cache_key]
    except Exception as e:
        logger.error(f"Error in remove_restricted_role GID {guild_id} RID {role_id}: {e}", exc_info=True)
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def get_command_restrictions_for_role(guild_id: int, guild_name_for_path: str, role_id: int) -> list[dict]:
    """Get all command restrictions for a role."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_command_restrictions_for_role_sync(conn, role_id))
    except Exception as e:
        logger.error(f"Error in get_command_restrictions_for_role GID {guild_id} RID {role_id}: {e}", exc_info=True)
        return []
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def set_command_restriction(guild_id: int, guild_name_for_path: str, role_id: int, command_name: str, is_allowed: bool):
    """Set or update a command restriction for a role."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _set_command_restriction_sync(conn, role_id, command_name, is_allowed))
    except Exception as e:
        logger.error(f"Error in set_command_restriction GID {guild_id} RID {role_id}: {e}", exc_info=True)
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def remove_command_restriction(guild_id: int, guild_name_for_path: str, role_id: int, command_name: str):
    """Remove a command restriction for a role."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _remove_command_restriction_sync(conn, role_id, command_name))
    except Exception as e:
        logger.error(f"Error in remove_command_restriction GID {guild_id} RID {role_id}: {e}", exc_info=True)
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def get_all_command_restrictions(guild_id: int, guild_name_for_path: str) -> list[dict]:
    """Get all command restrictions for all roles."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_all_command_restrictions_sync(conn))
    except Exception as e:
        logger.error(f"Error in get_all_command_restrictions GID {guild_id}: {e}", exc_info=True)
        return []
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)

async def is_command_allowed_for_role(guild_id: int, guild_name_for_path: str, role_id: int, command_name: str) -> bool:
    """Check if a command is specifically allowed for a role."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "restricted_roles.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _is_command_allowed_for_role_sync(conn, role_id, command_name))
    except Exception as e:
        logger.error(f"Error in is_command_allowed_for_role GID {guild_id} RID {role_id}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            await _core._release_db_async(guild_id, "restricted_roles.db", guild_name_for_path, conn)
