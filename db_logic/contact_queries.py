# db_logic/contact_queries.py
from . import _core
import logging

logger = logging.getLogger('discord_bot_database')

# --- Synchronous Functions ---

def _register_contact_info_sync(conn, user_id: int, user_name: str, email: str, payment_method: str):
    """Register or update contact information for a user."""
    with conn: conn.execute("""
        INSERT INTO contact_info (user_id, user_name, email, payment_method) 
        VALUES (?, ?, ?, ?) 
        ON CONFLICT(user_id) DO UPDATE SET 
            user_name=excluded.user_name, 
            email=excluded.email, 
            payment_method=excluded.payment_method
    """, (user_id, user_name, email, payment_method))

def _get_contact_info_sync(conn, user_id: int) -> dict | None:
    """Get contact information for a user."""
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, user_name, email, payment_method FROM contact_info WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def _get_all_contact_info_for_export_sync(conn) -> list:
    """Get all contact information for export."""
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, user_name, email, payment_method FROM contact_info ORDER BY user_name")
    return [dict(row) for row in cursor.fetchall()]

# --- Public Async Functions ---

async def register_contact_info(guild_id: int, guild_name_for_path: str, user_id: int, user_name: str, email: str, payment_method: str):
    """Register or update contact information for a user."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "contact_info.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _register_contact_info_sync(conn, user_id, user_name, email, payment_method))
    except Exception as e:
        logger.error(f"Error in register_contact_info GID {guild_id} UID {user_id}: {e}", exc_info=True)
    finally:
        if conn:
            await _core._release_db_async(guild_id, "contact_info.db", guild_name_for_path, conn)

async def get_contact_info(guild_id: int, guild_name_for_path: str, user_id: int) -> dict | None:
    """Get contact information for a user."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "contact_info.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_contact_info_sync(conn, user_id))
    except Exception as e:
        logger.error(f"Error in get_contact_info GID {guild_id} UID {user_id}: {e}", exc_info=True)
        return None
    finally:
        if conn:
            await _core._release_db_async(guild_id, "contact_info.db", guild_name_for_path, conn)

async def get_all_contact_info_for_export(guild_id: int, guild_name_for_path: str) -> list:
    """Get all contact information for export."""
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "contact_info.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_all_contact_info_for_export_sync(conn))
    except Exception as e:
        logger.error(f"Error in get_all_contact_info_for_export GID {guild_id}: {e}", exc_info=True)
        return []
    finally:
        if conn:
            await _core._release_db_async(guild_id, "contact_info.db", guild_name_for_path, conn)

async def get_user_email_by_id(guild_id: int, guild_name_for_path: str, user_id: int) -> str | None:
    """Get a user's email from contact info."""
    contact_info = await get_contact_info(guild_id, guild_name_for_path, user_id)
    return contact_info.get("email") if contact_info else None

async def get_user_payment_method_by_id(guild_id: int, guild_name_for_path: str, user_id: int) -> str | None:
    """Get a user's payment method from contact info."""
    contact_info = await get_contact_info(guild_id, guild_name_for_path, user_id)
    return contact_info.get("payment_method") if contact_info else None
