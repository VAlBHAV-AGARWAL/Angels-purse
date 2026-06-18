# cogs/auto_backup.py
import discord
from discord.ext import commands, tasks
import os
import zipfile
import database
from datetime import datetime, time, timezone
import logging
import asyncio

logger = logging.getLogger('cog.auto_backup')
BACKUP_DIR = "automatic_backups"
os.makedirs(BACKUP_DIR, exist_ok=True)
BACKUP_TIME_UTC = time(hour=3, minute=0, tzinfo=timezone.utc) # Set to a low-traffic time

class AutoBackupCog(commands.Cog, name="AutoBackup"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_backup_task.start()
        logger.info("AutoBackupCog loaded and daily backup task started.")

    def cog_unload(self):
        self.daily_backup_task.cancel()

    def _sync_backup_guild(self, guild_id: int, guild_name: str) -> str | None:
        try:
            guild_backup_dir = os.path.join(BACKUP_DIR, str(guild_id))
            os.makedirs(guild_backup_dir, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            zip_filename = f"{database.sanitize_name(guild_name)}_auto_backup_{timestamp}.zip"
            zip_filepath = os.path.join(guild_backup_dir, zip_filename)
            
            # CORRECTED: Pass guild_name to the database function
            db_paths = database.get_all_db_paths_for_guild(guild_id, guild_name)

            if not db_paths:
                logger.warning(f"No DB files for guild {guild_id} during auto-backup.")
                return None
            
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for db_path in db_paths:
                    if os.path.exists(db_path):
                        zipf.write(db_path, arcname=os.path.basename(db_path))
            return zip_filepath
        except Exception as e:
            logger.error(f"Error creating backup for guild {guild_id}: {e}", exc_info=True)
            return None

    @tasks.loop(time=BACKUP_TIME_UTC)
    async def daily_backup_task(self):
        logger.info("Starting daily backup task for all guilds...")
        for guild in self.bot.guilds:
            try:
                zip_file_path = await self.bot.loop.run_in_executor(None, self._sync_backup_guild, guild.id, guild.name)
                if zip_file_path:
                    logger.info(f"Auto-backup successful for guild {guild.name} ({guild.id})")
                else:
                    logger.warning(f"Auto-backup failed for guild {guild.name} ({guild.id}).")
            except Exception as e:
                logger.error(f"Unhandled exception during backup for guild {guild.name} ({guild.id}): {e}", exc_info=True)
            await asyncio.sleep(1)
        logger.info("Daily backup task completed.")

    @daily_backup_task.before_loop
    async def before_daily_backup_task(self):
        await self.bot.wait_until_ready()
        logger.info("Daily backup task is ready.")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoBackupCog(bot))