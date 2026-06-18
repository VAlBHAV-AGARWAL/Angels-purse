# cogs/settings.py (Permission Bypass Fix)
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
import logging
from utils.styles import COLORS, EMOJIS
from utils.checks import check_failure_error_handler, actual_is_not_restricted_check
import database

from .settings_views.assignment_view import AssignmentSettingsView
from .settings_views.task_view import TaskManagementView
from .settings_views.rate_view import RateManagementView
from .settings_views.restriction_view import RestrictionManagementView
from .settings_views.data_view import DataManagementView

logger = logging.getLogger('cog.settings')

class SettingsMainView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True

    @ui.button(label="Assignment Settings", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def assignment_settings(self, interaction: Interaction, button: ui.Button):
        enabled_formats = await database.get_enabled_formats(interaction.guild_id, interaction.guild.name)
        view = AssignmentSettingsView(self.original_interaction, enabled_formats)
        embed = view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @ui.button(label="Task Management", style=discord.ButtonStyle.secondary, emoji="📜")
    async def task_management(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(title="📜 Task Management", description="Manage your server's tasks.", color=COLORS["INFO"])
        view = TaskManagementView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="Rate Management", style=discord.ButtonStyle.secondary, emoji="📈")
    async def rate_management(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(title="📈 Rate Management", description="Manage rates for tasks.", color=COLORS["INFO"])
        view = RateManagementView(self.original_interaction)
        # This function doesn't exist, we should remove it or implement it. Removing for now.
        # await view.update_buttons(interaction)
        await interaction.response.edit_message(embed=embed, view=view)

    @ui.button(label="Restriction Management", style=discord.ButtonStyle.secondary, emoji="🔒", row=1)
    async def restriction_management(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(title="🔒 Restriction Management", description="Manage role permissions.", color=COLORS["INFO"])
        view = RestrictionManagementView(self.original_interaction)
        await view.refresh(interaction)

    @ui.button(label="Server Data", style=discord.ButtonStyle.danger, emoji="🗄️", row=1)
    async def server_data(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(title="🗄️ Server Data Management", description="Create backups, export data, or clear data.", color=COLORS["INFO"])
        view = DataManagementView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)

class SettingsCog(commands.Cog, name="Settings"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("SettingsCog loaded.")

    @app_commands.command(name="settings", description="[Admin] Access the main settings panel.")
    @app_commands.guild_only()
    # --- THIS LINE IS THE FIX ---
    # @app_commands.default_permissions(administrator=True)  <- This line has been removed.
    @app_commands.check(actual_is_not_restricted_check) # Now this check is the ONLY gatekeeper.
    async def settings(self, interaction: Interaction):
        embed = discord.Embed(title=f"{EMOJIS['TOOL']} Bot Settings Panel", description="Select a category to configure.", color=COLORS["PRIMARY"])
        view = SettingsMainView(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @settings.error
    async def settings_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await check_failure_error_handler(interaction, error)

async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))