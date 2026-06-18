# db_logic/rate_queries.py (Verified Final Version)
import discord
from typing import Optional, Union, List, Dict
import json
from . import _core
import logging

logger = logging.getLogger('discord_bot_database')

# --- Universal Synchronous Helpers ---
def _get_rates_sync(conn, table: str, key_column: str, key_value) -> Dict[str, float]:
    query = f"SELECT rates_json FROM {table} WHERE {key_column} = ?"
    cursor = conn.cursor()
    cursor.execute(query, (key_value,))
    row = cursor.fetchone()
    return json.loads(row['rates_json']) if row and row['rates_json'] else {}

def _set_rates_sync(conn, table: str, key_column: str, key_value, rates: Dict[str, float]):
    query = f"INSERT INTO {table} ({key_column}, rates_json) VALUES (?, ?) ON CONFLICT({key_column}) DO UPDATE SET rates_json = excluded.rates_json"
    with conn: conn.execute(query, (key_value, json.dumps(rates)))

def _delete_rate_sync(conn, table: str, key_column: str, key_value, task_name: str):
    rates = _get_rates_sync(conn, table, key_column, key_value)
    if task_name in rates:
        del rates[task_name]
        _set_rates_sync(conn, table, key_column, key_value, rates)

def _get_context_rate_sync(conn, context_id: int) -> dict:
    cursor = conn.cursor()
    cursor.execute("SELECT rates_json FROM forum_rates WHERE context_id = ?", (context_id,))
    row = cursor.fetchone()
    return json.loads(row['rates_json']) if row and row['rates_json'] else {}

def _set_context_rate_sync(conn, context_id: int, context_type: str, rates: dict):
    query = "INSERT INTO forum_rates (context_id, context_type, rates_json) VALUES (?, ?, ?) ON CONFLICT(context_id) DO UPDATE SET rates_json = excluded.rates_json, context_type = excluded.context_type"
    with conn: conn.execute(query, (context_id, context_type, json.dumps(rates)))

def _delete_context_rate_sync(conn, context_id: int, task_name: str):
    rates = _get_context_rate_sync(conn, context_id)
    if task_name in rates:
        del rates[task_name]
        with conn: conn.execute("UPDATE forum_rates SET rates_json = ? WHERE context_id = ?", (json.dumps(rates), context_id))

def _delete_rates_for_task_sync(conn, table: str, task_name_upper: str):
    key_column = "channel_id" if table == "channel_rates" else "context_id"
    cursor = conn.cursor()
    cursor.execute(f"SELECT {key_column}, rates_json FROM {table}")
    to_update = []
    for row in cursor.fetchall():
        rates = json.loads(row['rates_json']) if row['rates_json'] else {}
        if task_name_upper in rates:
            del rates[task_name_upper]
            to_update.append((json.dumps(rates), row[key_column]))
    if to_update:
        with conn: conn.executemany(f"UPDATE {table} SET rates_json = ? WHERE {key_column} = ?", to_update)

# --- Public Async Functions ---
async def get_default_rates(gid, gname): return await _get_rates_async(gid, gname, "default_rates", "id", 1)
async def get_channel_rates(gid, gname, cid): return await _get_rates_async(gid, gname, "channel_rates", "channel_id", cid)
async def get_forum_rates(gid, gname, fid): return await _get_context_rates_async(gid, gname, fid)
async def get_post_rates(gid, gname, pid): return await _get_context_rates_async(gid, gname, pid)

async def update_default_rates(gid, gname, new_rates: Dict[str, float]): await _update_rates_async(gid, gname, "default_rates", "id", 1, new_rates)
async def update_channel_rates(gid, gname, cid, new_rates: Dict[str, float]): await _update_rates_async(gid, gname, "channel_rates", "channel_id", cid, new_rates)
async def update_forum_rates(gid, gname, fid, new_rates: Dict[str, float]): await _update_context_rates_async(gid, gname, fid, "forum", new_rates)
async def update_post_rates(gid, gname, pid, new_rates: Dict[str, float]): await _update_context_rates_async(gid, gname, pid, "post", new_rates)

async def delete_default_rate(gid, gname, task): await _delete_rate_async(gid, gname, "default_rates", "id", 1, task)
async def delete_channel_rate(gid, gname, cid, task): await _delete_rate_async(gid, gname, "channel_rates", "channel_id", cid, task)
async def delete_forum_rate(gid, gname, fid, task): await _delete_context_rate_async(gid, gname, fid, task)
async def delete_post_rate(gid, gname, pid, task): await _delete_context_rate_async(gid, gname, pid, task)

async def delete_channel_rates_for_task(gid, gname, task):
    conn = None
    try:
        conn = await _core._connect_db_async(gid, "rates.db", gname)
        await _core._run_in_executor(lambda: _delete_rates_for_task_sync(conn, "channel_rates", task))
    finally:
        if conn: await _core._release_db_async(gid, "rates.db", gname, conn)

async def get_effective_rate(gid, gname, task, context: Union[discord.TextChannel, discord.Thread]) -> tuple[Optional[float], str]:
    if isinstance(context, discord.Thread):
        post_rates = await get_post_rates(gid, gname, context.id)
        if task in post_rates:
            return post_rates[task], f"a specific rate for the post {context.mention}"
        if isinstance(context.parent, discord.ForumChannel):
            forum_rates = await get_forum_rates(gid, gname, context.parent.id)
            if task in forum_rates:
                return forum_rates[task], f"a rate for the forum '{context.parent.name}'"
    if isinstance(context, discord.TextChannel):
        channel_rates = await get_channel_rates(gid, gname, context.id)
        if task in channel_rates:
            return channel_rates[task], f"a rate for the channel {context.mention}"
    default_rates = await get_default_rates(gid, gname)
    if task in default_rates:
        return default_rates[task], "the server's default rate"
    return None, "No rate set"

# --- Helper Coroutines ---
async def _get_rates_async(gid, gname, table, key_col, key_val):
    conn = None
    try:
        conn = await _core._connect_db_async(gid, "rates.db", gname)
        return await _core._run_in_executor(lambda: _get_rates_sync(conn, table, key_col, key_val))
    finally:
        if conn: await _core._release_db_async(gid, "rates.db", gname, conn)

async def _update_rates_async(gid, gname, table, key_col, key_val, new_rates):
    current_rates = await _get_rates_async(gid, gname, table, key_col, key_val)
    current_rates.update(new_rates)
    conn = None
    try:
        conn = await _core._connect_db_async(gid, "rates.db", gname)
        await _core._run_in_executor(lambda: _set_rates_sync(conn, table, key_col, key_val, current_rates))
    finally:
        if conn: await _core._release_db_async(gid, "rates.db", gname, conn)
        
async def _delete_rate_async(gid, gname, table, key_col, key_val, task):
    conn = None
    try:
        conn = await _core._connect_db_async(gid, "rates.db", gname)
        await _core._run_in_executor(lambda: _delete_rate_sync(conn, table, key_col, key_val, task))
    finally:
        if conn: await _core._release_db_async(gid, "rates.db", gname, conn)

async def _get_context_rates_async(gid, gname, ctx_id):
    conn = None
    try:
        conn = await _core._connect_db_async(gid, "rates.db", gname)
        return await _core._run_in_executor(lambda: _get_context_rate_sync(conn, ctx_id))
    finally:
        if conn: await _core._release_db_async(gid, "rates.db", gname, conn)

async def _update_context_rates_async(gid, gname, ctx_id, ctx_type, new_rates):
    current_rates = await _get_context_rates_async(gid, gname, ctx_id)
    current_rates.update(new_rates)
    conn = None
    try:
        conn = await _core._connect_db_async(gid, "rates.db", gname)
        await _core._run_in_executor(lambda: _set_context_rate_sync(conn, ctx_id, ctx_type, current_rates))
    finally:
        if conn: await _core._release_db_async(gid, "rates.db", gname, conn)

async def _delete_context_rate_async(gid, gname, ctx_id, task):
    conn = None
    try:
        conn = await _core._connect_db_async(gid, "rates.db", gname)
        await _core._run_in_executor(lambda: _delete_context_rate_sync(conn, ctx_id, task))
    finally:
        if conn: await _core._release_db_async(gid, "rates.db", gname, conn)