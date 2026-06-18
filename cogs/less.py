# cogs/less.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import database
from utils.checks import check_failure_error_handler, actual_is_not_restricted_check
from utils.autocompletes import context_autocomplete # <-- IMPORT a
import logging
from datetime import datetime
from utils.styles import COLORS, EMOJIS, format_currency
from typing import List

logger = logging.getLogger('cog.less')

class LessCog(commands.Cog, name="EconomyLess"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # The local context_autocomplete function has been removed.

    async def task_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not interaction.guild: return []
        try:
            tasks = await database.get_task_names(interaction.guild_id, interaction.guild.name)
            return [app_commands.Choice(name=task, value=task) for task in tasks if current.lower() in task.lower()][:25]
        except Exception:
            return []

    @app_commands.command(name="less", description="[Admin] Remove currency from a user's balance.")
    @app_commands.guild_only()
    @app_commands.check(actual_is_not_restricted_check)
    @app_commands.describe(user="The user to remove currency from. Defaults to yourself.", amount="The amount of currency to remove.", context="The channel or forum post related to this removal.", task="The task name for this removal.", reason="The reason for removing currency.")
    @app_commands.autocomplete(context=context_autocomplete, task=task_autocomplete) # <-- USE a
    async def less(self, interaction: Interaction, amount: app_commands.Range[float, 0.01, None], context: str, task: str, reason: str, user: discord.Member = None):
        target_user = user or interaction.user
        if target_user.id != interaction.user.id:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You have permission to use `/less`, but only for yourself. Administrator permissions are required to affect other users.", ephemeral=True)
                return
        if target_user.bot:
            await interaction.response.send_message("You cannot remove currency from a bot!", ephemeral=True)
            return
        try:
            context_id = int(context)
            context_obj = interaction.guild.get_channel_or_thread(context_id)
            if context_obj is None:
                context_obj = await interaction.guild.fetch_channel(context_id)
        except (ValueError, discord.NotFound, discord.Forbidden):
            await interaction.response.send_message("Invalid context selected or I can't see that channel/post.", ephemeral=True)
            return
        guild_id, guild_name = interaction.guild_id, interaction.guild.name
        await interaction.response.defer(ephemeral=False)
        enabled_formats = await database.get_enabled_formats(guild_id, guild_name)
        context_data, context_mention, error_msg = {}, "", None
        if isinstance(context_obj, discord.TextChannel):
            if 'channel_based' in enabled_formats:
                context_data = {"channel_id": context_obj.id, "channel_name": context_obj.name}
                context_mention = context_obj.mention
            else: error_msg = "Removing funds via Text Channel is disabled."
        elif isinstance(context_obj, discord.Thread):
            if 'post_based' in enabled_formats:
                context_data = {"post_id": context_obj.id, "channel_name": context_obj.name}
                context_mention = context_obj.mention
            elif 'forum_based' in enabled_formats and isinstance(context_obj.parent, discord.ForumChannel):
                context_data = {"forum_id": context_obj.parent.id, "channel_name": context_obj.parent.name}
                context_mention = context_obj.parent.mention
            else: error_msg = "Removing funds via Forum Post is disabled."
        else:
            error_msg = "Invalid context provided."
        if error_msg:
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        task_upper = task.upper()
        if not await database.get_task(guild_id, guild_name, task_upper):
            await interaction.followup.send(f"Task '{task}' not found.", ephemeral=True)
            return
        success = await database.remove_money(guild_id, guild_name, target_user.id, target_user.name, amount, reason, task_upper, interaction.user.id, interaction.user.name, context_data)
        if success:
            embed = discord.Embed(title=f"{EMOJIS['MONEY']} Money Removed", description=f"{EMOJIS['REMOVE']} Removed **{format_currency(amount)}** from {target_user.mention} for work in {context_mention} on **{discord.utils.escape_markdown(task_upper)}**.", color=COLORS["RUBY"], timestamp=datetime.now()).add_field(name="Reason", value=discord.utils.escape_markdown(reason))
            if target_user.avatar: embed.set_thumbnail(url=target_user.avatar.url)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Failed to remove currency. An error occurred.", ephemeral=True)

    @less.error
    async def less_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await check_failure_error_handler(interaction, error)

async def setup(bot: commands.Bot):
    await bot.add_cog(LessCog(bot))