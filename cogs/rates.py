# cogs/rates.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import database
from utils.autocompletes import context_autocomplete # <-- IMPORT a
from typing import Optional, List
import logging
from utils.styles import COLORS, EMOJIS

logger = logging.getLogger('cog.rates')

class RatesCog(commands.Cog, name="RateViewing"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("RatesCog loaded. Management commands are now in /settings.")

    # The local context_autocomplete function has been removed.

    async def task_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        if not interaction.guild: return []
        try:
            tasks = await database.get_task_names(interaction.guild_id, interaction.guild.name)
            return [app_commands.Choice(name=name, value=name) for name in tasks if current.lower() in name.lower()][:25]
        except Exception:
            return []

    @app_commands.command(name="rates", description="Get the effective rate for a task in a specific context.")
    @app_commands.guild_only()
    @app_commands.describe(
        task_name="The name of the task to check.",
        context="The channel or forum post to check the rate for (defaults to current)."
    )
    @app_commands.autocomplete(task_name=task_autocomplete, context=context_autocomplete) # <-- USE a
    async def rates(self, interaction: Interaction, task_name: str, context: Optional[str] = None):
        
        target_context = None
        if context:
            try:
                context_id = int(context)
                target_context = interaction.guild.get_channel_or_thread(context_id)
                if target_context is None:
                    target_context = await interaction.guild.fetch_channel(context_id)
            except (ValueError, discord.NotFound, discord.Forbidden):
                await interaction.response.send_message("Invalid context selected or I can't see that channel/post.", ephemeral=True)
                return
        else:
            target_context = interaction.channel

        if not isinstance(target_context, (discord.TextChannel, discord.Thread)):
             await interaction.response.send_message("Please specify a text channel/post or use this command within one.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=True)
        
        guild_id, guild_name = interaction.guild_id, interaction.guild.name
        task_name_upper = task_name.upper()

        if not await database.get_task(guild_id, guild_name, task_name_upper):
            await interaction.followup.send(f"Task '{task_name_upper}' is not defined.", ephemeral=True)
            return

        rate, source = await database.get_effective_rate(guild_id, guild_name, task_name_upper, target_context)

        if rate is not None:
            embed = discord.Embed(
                title=f"{EMOJIS['CHART_UP']} Rate for: {task_name_upper}",
                description=f"The effective rate is **${rate:,.2f}**.",
                color=COLORS["SUCCESS"]
            ).add_field(name="Source", value=f"This rate was determined by {source}.")
        else:
            embed = discord.Embed(
                title=f"{EMOJIS['THINK']} Rate Not Found",
                description=f"No rate has been set for **{task_name_upper}** in this context or as a server default.",
                color=COLORS["WARNING"]
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RatesCog(bot))