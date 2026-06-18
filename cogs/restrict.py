# cogs/restrict.py (Decommissioned)
import discord
from discord.ext import commands
import logging

logger = logging.getLogger('cog.restrict')

class RestrictionCog(commands.Cog, name="RestrictionManagement"):
    """
    Handles the loading of the cog. 
    All restriction management commands are now located in the /settings panel.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("RestrictionCog loaded. Management commands are in /settings.")

async def setup(bot: commands.Bot):
    await bot.add_cog(RestrictionCog(bot))