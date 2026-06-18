# db_logic/task_queries.py
from . import _core
import logging

logger = logging.getLogger('discord_bot_database')

# --- Synchronous Functions ---

def _add_task_sync(conn, task_name_upper: str, rank: int):
    """Add or update a task in the tasks table."""
    with conn: conn.execute("INSERT OR REPLACE INTO tasks (task_name, rank) VALUES (?, ?)", (task_name_upper, rank))

def _remove_task_sync(conn, task_name_upper: str):
    """Remove a task from the tasks table."""
    with conn: conn.execute("DELETE FROM tasks WHERE task_name = ?", (task_name_upper,))

def _get_task_sync(conn, task_name_upper: str) -> dict | None:
    """Get a specific task by name."""
    cursor = conn.cursor()
    cursor.execute("SELECT task_name, rank FROM tasks WHERE task_name = ?", (task_name_upper,))
    row = cursor.fetchone()
    return dict(row) if row else None

def _get_tasks_sync(conn) -> list:
    """Get all tasks ordered by rank and name."""
    cursor = conn.cursor()
    cursor.execute("SELECT task_name, rank FROM tasks ORDER BY rank, task_name")
    return [dict(row) for row in cursor.fetchall()]

# --- Public Async Functions ---

async def get_tasks(guild_id: int, guild_name_for_path: str) -> list:
    """Get all tasks for a guild with caching."""
    cache_key = _core._get_cache_key(guild_id, guild_name_for_path)
    
    # Try to get from cache first
    cached_tasks = _core._get_cached_data(_core._task_cache, cache_key)
    if cached_tasks is not None:
        return cached_tasks
    
    # If not in cache, get from database
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "tasks.db", guild_name_for_path)
        result = await _core._run_in_executor(lambda: _get_tasks_sync(conn)) or []
        
        # Update cache
        _core._update_cache(_core._task_cache, cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"Error in get_tasks GID {guild_id}: {e}", exc_info=True)
        return []
    finally:
        if conn:
            await _core._release_db_async(guild_id, "tasks.db", guild_name_for_path, conn)

async def add_task(guild_id: int, guild_name_for_path: str, task_name_upper: str, rank: int):
    """Add or update a task with cache invalidation."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "tasks.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _add_task_sync(conn, task_name_upper, rank))
        
        # Invalidate cache
        cache_key = _core._get_cache_key(guild_id, guild_name_for_path)
        if cache_key in _core._task_cache:
            del _core._task_cache[cache_key]
    except Exception as e:
        logger.error(f"Error in add_task GID {guild_id} Task '{task_name_upper}': {e}", exc_info=True)
    finally:
        if conn:
            await _core._release_db_async(guild_id, "tasks.db", guild_name_for_path, conn)

async def remove_task(guild_id: int, guild_name_for_path: str, task_name_upper: str):
    """Remove a task with cache invalidation."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "tasks.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _remove_task_sync(conn, task_name_upper))
        
        # Invalidate cache
        cache_key = _core._get_cache_key(guild_id, guild_name_for_path)
        if cache_key in _core._task_cache:
            del _core._task_cache[cache_key]
    except Exception as e:
        logger.error(f"Error in remove_task GID {guild_id} Task '{task_name_upper}': {e}", exc_info=True)
    finally:
        if conn:
            await _core._release_db_async(guild_id, "tasks.db", guild_name_for_path, conn)

async def get_task(guild_id: int, guild_name_for_path: str, task_name_upper: str) -> dict | None:
    """Get a specific task by name."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "tasks.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_task_sync(conn, task_name_upper))
    except Exception as e:
        logger.error(f"Error in get_task GID {guild_id} Task '{task_name_upper}': {e}", exc_info=True)
        return None
    finally:
        if conn:
            await _core._release_db_async(guild_id, "tasks.db", guild_name_for_path, conn)

async def get_task_names(guild_id: int, guild_name_for_path: str) -> list[str]:
    """Get all task names for a guild."""
    tasks = await get_tasks(guild_id, guild_name_for_path)
    return [task.get('task_name', '') for task in tasks if task.get('task_name')]
