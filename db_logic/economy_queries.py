# db_logic/economy_queries.py (Reverted to not include 'payment')
from . import _core
from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Optional
import functools

logger = logging.getLogger('discord_bot_database')

# --- Synchronous Functions ---
def _update_user_sync(conn, user_id: int, user_name: str):
    with conn: conn.execute("INSERT INTO users (user_id, user_name, balance) VALUES (?, ?, 0.00) ON CONFLICT(user_id) DO UPDATE SET user_name = excluded.user_name", (user_id, user_name))

def _get_balance_sync(conn, user_id: int) -> float | None:
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row['balance'] if row else None

def _update_balance_sync(conn, user_id: int, new_balance: float):
    with conn: conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

def _log_transaction_sync(conn, data: dict):
    ts = datetime.now(timezone.utc).isoformat()
    keys = ["user_id", "user_name", "amount", "reason", "type", "channel_id", "channel_name", "task_name", "added_by_id", "added_by_name", "forum_id", "post_id", "thread_id"]
    for key in keys: data.setdefault(key, None)
    with conn:
        conn.execute("""
            INSERT INTO transactions (user_id, user_name, amount, reason, timestamp, type, channel_id, channel_name, task_name, added_by_id, added_by_name, forum_id, post_id, thread_id)
            VALUES (:user_id, :user_name, :amount, :reason, :timestamp, :type, :channel_id, :channel_name, :task_name, :added_by_id, :added_by_name, :forum_id, :post_id, :thread_id)
        """, {**data, "timestamp": ts})

def _get_leaderboard_sync(conn, limit: int | None) -> list:
    query = "SELECT user_id, user_name, balance FROM users ORDER BY balance DESC"
    if limit is not None: query += f" LIMIT {limit}"
    cursor = conn.cursor()
    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]

def _get_transactions_sync(conn, user_id: int | None = None, context_id: int | None = None, limit: int | None = 25, offset: int = 0) -> list:
    query = "SELECT * FROM transactions"
    conditions, params = [], []
    if user_id is not None:
        conditions.append("user_id = ?"); params.append(user_id)
    if context_id is not None:
        conditions.append("(channel_id = ? OR forum_id = ? OR post_id = ?)"); params.extend([context_id, context_id, context_id])
    if conditions: query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC"
    if limit is not None: query += f" LIMIT ? OFFSET ?"; params.extend([limit, offset])
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

def _get_transaction_by_id_sync(conn, transaction_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    result = cursor.fetchone()
    return dict(result) if result else None

def _update_transaction_sync(conn, transaction_id: int, reason: str | None = None, amount: float | None = None, task_name: str | None = None, user_name: str | None = None, added_by_id: int | None = None, added_by_name: str | None = None) -> bool:
    updates, params = [], []
    if reason is not None: updates.append("reason = ?"); params.append(reason)
    if amount is not None: updates.append("amount = ?"); params.append(amount)
    if task_name is not None: updates.append("task_name = ?"); params.append(task_name)
    if user_name is not None: updates.append("user_name = ?"); params.append(user_name)
    if added_by_id is not None: updates.append("added_by_id = ?"); params.append(added_by_id)
    if added_by_name is not None: updates.append("added_by_name = ?"); params.append(added_by_name)
    if not updates: return True
    query = f"UPDATE transactions SET {', '.join(updates)} WHERE transaction_id = ?"
    params.append(transaction_id)
    with conn: conn.execute(query, tuple(params))
    return True

def _delete_transaction_sync(conn, transaction_id: int) -> bool:
    with conn: conn.execute("DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,))
    return True

def _get_all_users_sync(conn) -> list:
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, user_name, balance FROM users ORDER BY user_name")
    return [dict(row) for row in cursor.fetchall()]

# --- Public Async Functions ---
async def get_balance(guild_id: int, guild_name_for_path: str, user_id: int, user_name: str | None = None) -> float:
    cache_key = _core._get_cache_key(guild_id, guild_name_for_path, user_id)
    cached_balance = _core._get_cached_data(_core._user_balance_cache, cache_key)
    if cached_balance is not None: return cached_balance
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        balance = await _core._run_in_executor(lambda: _get_balance_sync(conn, user_id))
        if user_name is not None: await update_user(guild_id, guild_name_for_path, user_id, user_name)
        if balance is not None: _core._update_cache(_core._user_balance_cache, cache_key, balance)
        return balance if balance is not None else 0.0
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def update_balance(guild_id: int, guild_name_for_path: str, user_id: int, new_balance: float):
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _update_balance_sync(conn, user_id, new_balance))
        cache_key = _core._get_cache_key(guild_id, guild_name_for_path, user_id)
        _core._update_cache(_core._user_balance_cache, cache_key, new_balance)
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def update_user(guild_id: int, guild_name_for_path: str, user_id: int, user_name: str):
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _update_user_sync(conn, user_id, user_name))
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def log_transaction(guild_id: int, guild_name_for_path: str, data: dict):
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _log_transaction_sync(conn, data))
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def add_money(guild_id: int, guild_name_for_path: str, user_id: int, user_name: str, amount: float, reason: str, task_name: str | None, actor_id: int, actor_name: str, context: dict):
    if amount <= 0: return False
    await update_user(guild_id, guild_name_for_path, user_id, user_name)
    current_balance = await get_balance(guild_id, guild_name_for_path, user_id)
    new_balance = current_balance + amount
    await update_balance(guild_id, guild_name_for_path, user_id, new_balance)
    log_data = {"user_id": user_id, "user_name": user_name, "amount": amount, "reason": reason, "type": "add", "task_name": task_name, "added_by_id": actor_id, "added_by_name": actor_name, **context}
    await log_transaction(guild_id, guild_name_for_path, log_data)
    return True

async def remove_money(guild_id: int, guild_name_for_path: str, user_id: int, user_name: str, amount: float, reason: str, task_name: str | None, actor_id: int, actor_name: str, context: dict):
    if amount <= 0: return False
    await update_user(guild_id, guild_name_for_path, user_id, user_name)
    current_balance = await get_balance(guild_id, guild_name_for_path, user_id)
    new_balance = current_balance - amount
    await update_balance(guild_id, guild_name_for_path, user_id, new_balance)
    log_data = {"user_id": user_id, "user_name": user_name, "amount": amount, "reason": reason, "type": "less", "task_name": task_name, "added_by_id": actor_id, "added_by_name": actor_name, **context}
    await log_transaction(guild_id, guild_name_for_path, log_data)
    return True

async def get_leaderboard(guild_id: int, guild_name_for_path: str, limit: int | None = None) -> list:
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_leaderboard_sync(conn, limit))
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

get_leaderboard_data = get_leaderboard

async def get_all_users(guild_id: int, guild_name_for_path: str) -> list:
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_all_users_sync(conn))
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def get_transactions(guild_id: int, guild_name_for_path: str, user_id: int | None = None, context_id: int | None = None, limit: int | None = 25, offset: int = 0) -> list:
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_transactions_sync(conn, user_id, context_id, limit, offset))
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

get_all_transactions = functools.partial(get_transactions, limit=None, offset=0)
get_user_transactions = functools.partial(get_transactions, context_id=None)

async def get_transaction_by_id(guild_id: int, guild_name_for_path: str, transaction_id: int) -> dict | None:
    conn = None
    try:
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        return await _core._run_in_executor(lambda: _get_transaction_by_id_sync(conn, transaction_id))
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def update_transaction(guild_id: int, guild_name_for_path: str, transaction_id: int, reason: str | None = None, amount: float | None = None, task_name: str | None = None, user_name: str | None = None, actor_id: int | None = None, actor_name: str | None = None) -> bool:
    conn = None
    try:
        old_transaction = await get_transaction_by_id(guild_id, guild_name_for_path, transaction_id)
        if not old_transaction: return False
        
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        result = await _core._run_in_executor(lambda: _update_transaction_sync(conn, transaction_id, reason, amount, task_name, user_name, actor_id, actor_name))
    
        if result and (amount is not None and old_transaction.get('amount', 0) != amount):
            user_id = old_transaction['user_id']
            await recalculate_user_balance(guild_id, guild_name_for_path, user_id)
            cache_key = _core._get_cache_key(guild_id, guild_name_for_path, user_id)
            if cache_key in _core._user_balance_cache: del _core._user_balance_cache[cache_key]
        
        return result
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)


async def delete_transaction(guild_id: int, guild_name_for_path: str, transaction_id: int) -> bool:
    conn = None
    try:
        transaction = await get_transaction_by_id(guild_id, guild_name_for_path, transaction_id)
        if not transaction: return False
        
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        result = await _core._run_in_executor(lambda: _delete_transaction_sync(conn, transaction_id))
        
        if result and 'user_id' in transaction:
            user_id = transaction['user_id']
            await recalculate_user_balance(guild_id, guild_name_for_path, user_id)
            cache_key = _core._get_cache_key(guild_id, guild_name_for_path, user_id)
            if cache_key in _core._user_balance_cache: del _core._user_balance_cache[cache_key]
        
        return result
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)

async def recalculate_user_balance(guild_id: int, guild_name_for_path: str, user_id: int) -> float | None:
    conn = None
    try:
        all_transactions = await get_user_transactions(guild_id, guild_name_for_path, user_id, limit=None)
        balance = sum(tx['amount'] if tx.get('type') == 'add' else -tx['amount'] for tx in all_transactions)
        
        conn = await _core._connect_db_async(guild_id, "economy.db", guild_name_for_path)
        await _core._run_in_executor(lambda: _update_balance_sync(conn, user_id, balance))
        
        cache_key = _core._get_cache_key(guild_id, guild_name_for_path, user_id)
        _core._update_cache(_core._user_balance_cache, cache_key, balance)
        
        return balance
    finally:
        if conn: await _core._release_db_async(guild_id, "economy.db", guild_name_for_path, conn)