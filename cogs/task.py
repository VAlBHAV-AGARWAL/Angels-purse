# cogs/task.py
import discord
from discord.ext import commands
import logging

logger = logging.getLogger('cog.task')

class TaskCog(commands.Cog, name="Task Management"):
    """
    Handles the loading of the cog. 
    All task management commands are now located in the /settings panel.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("TaskCog loaded. Management commands are in /settings.")

async def setup(bot: commands.Bot):
    await bot.add_cog(TaskCog(bot))