# database.py (The new, small facade)
import logging
import asyncio
import functools

# --- Import all public functions from the new logic modules ---
# The 'star' import is acceptable here as this file's sole purpose is to be a facade.
from db_logic.economy_queries import *
from db_logic.task_queries import *
from db_logic.rate_queries import *
from db_logic.restriction_queries import *
from db_logic.contact_queries import *
from db_logic.management_queries import *
from db_logic import _core

# Import sanitize_name function for use in other modules
from db_logic._core import sanitize_name
logger = logging.getLogger('discord_bot_database')

# --- Master Setup Functions that the bot will call ---

async def setup_database():
    """Initialize database module. Call this from main.py on bot startup."""
    asyncio.create_task(_core._cleanup_connection_pools())
    logger.info("Database connection pool maintenance task started.")

async def create_all_tables_for_guild(guild_id: int, guild_name_for_path: str):
    """Asynchronously creates all necessary database files and tables for a given guild."""
    connections = {
        "economy.db": (_core._create_economy_tables_sync, guild_id),
        "rates.db": (_core._create_rates_tables_sync,),
        "restricted_roles.db": (_core._create_restricted_roles_tables_sync,),
        "tasks.db": (_core._create_tasks_tables_sync,),
        "contact_info.db": (_core._create_contact_info_tables_sync,)
    }
    
    conn_list = []
    try:
        for db_name, (create_func, *args) in connections.items():
            conn = await _core._connect_db_async(guild_id, db_name, guild_name_for_path)
            conn_list.append((conn, db_name)) # Store conn and its db_name for release
            await _core._run_in_executor(functools.partial(create_func, conn, *args))
        
        logger.info(f"All database tables ensured for guild_id: {guild_id} ('{guild_name_for_path}')")
    except Exception as e:
        logger.error(f"Error creating all tables for guild {guild_id}: {e}", exc_info=True)
    finally:
        for conn, db_name in conn_list:
            if conn:
                await _core._release_db_async(guild_id, db_name, guild_name_for_path, conn)