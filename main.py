# main.py
import discord
from discord.ext import commands, tasks
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import asyncio
import database
from discord import app_commands

# Mahiru ECO Bot watermark
BOT_WATERMARK = "Mahiru"

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_OWNER_ID = os.getenv('BOT_OWNER_ID') # Load owner ID for checks
DEV_GUILD_ID = os.getenv('DEV_GUILD_ID')

if not BOT_OWNER_ID:
    print("CRITICAL: BOT_OWNER_ID is not set in the .env file. The permissions system will not function correctly.")

# --- Logging Setup ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file_path = os.path.join(LOG_DIR, "bot.log")
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setFormatter(log_formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if root_logger.hasHandlers():
    root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)
logger = logging.getLogger('discord_bot_main')

# --- Bot Intents ---
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
# Message content is not strictly needed for a pure slash command bot, but can be useful.
# We will keep it for now in case of future features.
intents.message_content = True 

# --- Bot Definition ---
# Prefix commands are disabled, but a prefix is still required. We use a non-standard prefix to avoid conflicts.
owner_id_int = int(BOT_OWNER_ID) if BOT_OWNER_ID else None
bot = commands.Bot(command_prefix="§§§", intents=intents, help_command=None, owner_id=owner_id_int)

bot.can_dm_owner = True
bot.watermark = BOT_WATERMARK

# --- Cog Loading ---
# List of cogs to load on startup. Old commands have been removed.
initial_extensions = [
    'cogs.add',
    'cogs.announce',
    'cogs.auto_backup',
    'cogs.bal',
    'cogs.balance',
    'cogs.help',
    'cogs.lb',
    'cogs.less',
    'cogs.ping',
    'cogs.rates',
    'cogs.register',
    'cogs.report',
    'cogs.settings', # The new central hub for admin commands
    'cogs.transaction_history',
    # The following cogs are now empty shells that just log a message.
    # They are kept for structural reference but could be removed entirely.
    'cogs.restrict',
    'cogs.task'
]

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    logger.info(f'Mahiru watermark active: {BOT_WATERMARK}')
    logger.info(f'Discord.py Version: {discord.__version__}')
    logger.info('Bot is ready and online!')
    
    try:
        await database.setup_database()
        logger.info("Database connection pool maintenance task started successfully.")
    except Exception as e:
        logger.error(f"Failed to set up database connection pool: {e}", exc_info=True)
    
    logger.info("Ensuring database tables for all connected guilds...")
    for guild in bot.guilds:
        try:
            logger.info(f"Ensuring all DB tables for guild: {guild.name} (ID: {guild.id})")
            await database.create_all_tables_for_guild(guild.id, guild.name)
        except Exception as e:
            logger.error(f"Failed to create tables for guild {guild.name} (ID: {guild.id}): {e}", exc_info=True)
    
    # The bot.command_aliases dictionary has been removed as it is no longer used.
    
    try:
        logger.info("Loading cogs...")
        for extension in sorted(initial_extensions): # Sorted for consistent load order
            try:
                await bot.load_extension(extension)
                logger.info(f'Successfully loaded extension: {extension}')
            except Exception as e:
                logger.error(f'Failed to load extension {extension}.', exc_info=e)

        # 1. Sync global commands (the 14 public ones)
        logger.info("Syncing global commands...")
        synced_global = await bot.tree.sync()
        logger.info(f"Successfully synced {len(synced_global)} slash command(s) globally.")

        # 2. Sync private commands to the developer guild
        if DEV_GUILD_ID:
            logger.info(f"Syncing private commands to developer guild (ID: {DEV_GUILD_ID})...")
            dev_guild_obj = discord.Object(id=DEV_GUILD_ID)
            # This makes all global commands ALSO appear instantly in your dev guild, which is great for testing
            bot.tree.copy_global_to(guild=dev_guild_obj)
            synced_dev = await bot.tree.sync(guild=dev_guild_obj)
            logger.info(f"Successfully synced {len(synced_dev)} command(s) to the developer guild.")
            
    except Exception as e:
        logger.error("Failed during bot setup.", exc_info=e)
        
    logger.info("Bot setup complete.")

@bot.event
async def on_guild_join(guild: discord.Guild):
    logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
    logger.info(f"Creating all database tables for {guild.name}...")
    await database.create_all_tables_for_guild(guild.id, guild.name)

@bot.event
async def on_guild_remove(guild: discord.Guild):
    logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")

if __name__ == "__main__":
    if DISCORD_TOKEN is None:
        logger.critical("CRITICAL: DISCORD_TOKEN is missing from your .env file.")
    else:
        try:
            logger.info("Starting bot...")
            bot.run(DISCORD_TOKEN)
        except discord.LoginFailure:
            logger.critical("CRITICAL: Failed to log in. Is your DISCORD_TOKEN correct?")
        except Exception as e:
            logger.critical(f"CRITICAL: An unexpected error occurred on bot startup: {e}", exc_info=True)