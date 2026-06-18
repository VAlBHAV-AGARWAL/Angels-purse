# cogs/settings_views/data_view.py (Final UI Fix)
import discord
from discord import ui, Interaction
import database
from utils import excel_utils
from utils.confirmation import ConfirmationView
from utils.styles import COLORS, EMOJIS
import os
import zipfile
from datetime import datetime, timezone
import io
import logging

logger = logging.getLogger('cog.data_view')

try:
    BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', 0))
except ValueError:
    BOT_OWNER_ID = 0

class ClearDataView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True
    @ui.button(label="Clear All Transactions", style=discord.ButtonStyle.danger, emoji="🔄", row=0)
    async def clear_transactions(self, interaction: Interaction, button: ui.Button):
        confirm_embed = discord.Embed(title="⚠️ Confirm Action", description="This will delete **ALL** transaction history and reset **ALL** user balances to zero. User registration data will be kept.\n\nThis is useful for starting a new season or payment period.\n**This action is irreversible.**", color=COLORS["WARNING"])
        confirm_view = ConfirmationView(user_id=interaction.user.id)
        await interaction.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
        await confirm_view.wait()
        if confirm_view.value:
            await interaction.edit_original_response(content=f"{EMOJIS['LOADING']} Processing...", view=None, embed=None)
            success = await database.clear_all_transactions(interaction.guild_id, interaction.guild.name)
            if success: await interaction.followup.send("✅ Successfully cleared all transactions and reset balances.", ephemeral=True)
            else: await interaction.followup.send("❌ An error occurred.", ephemeral=True)
    @ui.button(label="Clear a User's Data", style=discord.ButtonStyle.danger, emoji="👤", row=0)
    async def clear_user(self, interaction: Interaction, button: ui.Button):
        class UserSelectView(ui.View):
            def __init__(self, original_interaction):
                super().__init__(timeout=180)
                self.original_interaction = original_interaction
            @ui.select(cls=ui.UserSelect, placeholder="Select a user to clear their data...")
            async def select_user(self, inner_interaction: Interaction, select: ui.UserSelect):
                user_to_clear = select.values[0]
                confirm_embed = discord.Embed(title="⚠️ Confirm Action", description=f"This will delete all transactions for **{user_to_clear.mention}** and reset their balance to zero. Their registration info will be kept.\n\n**This action is irreversible.**", color=COLORS["WARNING"])
                confirm_view = ConfirmationView(user_id=inner_interaction.user.id)
                await inner_interaction.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if confirm_view.value:
                    await inner_interaction.edit_original_response(content=f"{EMOJIS['LOADING']} Processing...", view=None, embed=None)
                    success = await database.clear_user_economy_data(inner_interaction.guild_id, inner_interaction.guild.name, user_to_clear.id)
                    if success: await inner_interaction.followup.send(f"✅ Successfully cleared economy data for {user_to_clear.mention}.", ephemeral=True)
                    else: await inner_interaction.followup.send("❌ An error occurred.", ephemeral=True)
        await interaction.response.edit_message(content="Please select a user to clear their economic data (balance and transactions).", view=UserSelectView(interaction), embed=None)
    @ui.button(label="Clear ALL Server Data", style=discord.ButtonStyle.danger, emoji="💥", row=1)
    async def clear_all(self, interaction: Interaction, button: ui.Button):
        confirm_embed = discord.Embed(title="🔥🔥🔥 DANGER ZONE 🔥🔥🔥", description="You are about to delete **EVERYTHING** for this server: all users, all balances, all transactions, all registered emails, all tasks, and all rates. The bot will be reset to a completely clean slate.\n\n**THIS CANNOT BE UNDONE.**", color=COLORS["ERROR"])
        confirm_view = ConfirmationView(user_id=interaction.user.id)
        await interaction.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
        await confirm_view.wait()
        if confirm_view.value:
            await interaction.edit_original_response(content=f"{EMOJIS['LOADING']} Processing...", view=None, embed=None)
            success = await database.clear_all(interaction.guild_id, interaction.guild.name)
            if success: await interaction.followup.send("💥 Successfully cleared all server data.", ephemeral=True)
            else: await interaction.followup.send("❌ An error occurred.", ephemeral=True)
    @ui.button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=2)
    async def back(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(title="🗄️ Server Data Management", description="Create backups, export data, or clear data for this server.", color=COLORS["INFO"])
        view = DataManagementView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)

class ExportChoiceView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True
    @ui.button(label="Overview Export", style=discord.ButtonStyle.primary, emoji="📄")
    async def overview_export(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(content=f"{EMOJIS['LOADING']} Generating Overview Export... please wait.", view=None, embed=None)
        guild_id, guild_name = interaction.guild_id, interaction.guild.name
        try:
            excel_bytes_io = await excel_utils.create_excel_export(guild_id, guild_name, bot=interaction.client)
            if excel_bytes_io:
                filename = f"OverviewExport_{database.sanitize_name(guild_name)}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsx"
                await interaction.followup.send("Here is your Overview data export:", file=discord.File(excel_bytes_io, filename=filename), ephemeral=True)
                await interaction.edit_original_response(content="✅ Overview export generated successfully.")
            else: await interaction.edit_original_response(content="❌ Failed to generate the Excel export.")
        except Exception as e:
            logger.error(f"Error creating overview export for guild {guild_id}: {e}", exc_info=True)
            await interaction.edit_original_response(content=f"❌ An error occurred during the overview export.")
        self.stop()
    @ui.button(label="Detailed User Ledgers", style=discord.ButtonStyle.success, emoji="👥")
    async def detailed_export(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(content=f"{EMOJIS['LOADING']} Generating Detailed User Ledgers... this may take a moment.", view=None, embed=None)
        guild_id, guild_name = interaction.guild_id, interaction.guild.name
        try:
            excel_bytes_io = await excel_utils.create_user_ledgers_export(guild_id, guild_name)
            if excel_bytes_io:
                filename = f"UserLedgers_{database.sanitize_name(guild_name)}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsx"
                await interaction.followup.send("Here is your Detailed User Ledgers export:", file=discord.File(excel_bytes_io, filename=filename), ephemeral=True)
                await interaction.edit_original_response(content="✅ Detailed user ledger export generated successfully.")
            else: await interaction.edit_original_response(content="❌ Failed to generate the detailed export.")
        except Exception as e:
            logger.error(f"Error creating detailed export for guild {guild_id}: {e}", exc_info=True)
            await interaction.edit_original_response(content=f"❌ An error occurred during the detailed export.")
        self.stop()
    @ui.button(label="Cancel", style=discord.ButtonStyle.grey, row=1)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Export cancelled.", view=None, embed=None)
        self.stop()

class DataManagementView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        is_guild_owner = original_interaction.user.id == original_interaction.guild.owner_id
        is_bot_owner = original_interaction.user.id == BOT_OWNER_ID
        if is_guild_owner or is_bot_owner:
            backup_button = ui.Button(label="Create Backup", style=discord.ButtonStyle.primary, emoji="💾")
            backup_button.callback = self.create_backup
            self.add_item(backup_button)
        export_button = ui.Button(label="Export to Excel", style=discord.ButtonStyle.success, emoji="📄")
        export_button.callback = self.export_excel
        self.add_item(export_button)
        clear_data_button = ui.Button(label="Clear Data", style=discord.ButtonStyle.danger, emoji="⚠️")
        clear_data_button.callback = self.clear_data
        self.add_item(clear_data_button)
        back_button = ui.Button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=1)
        back_button.callback = self.back
        self.add_item(back_button)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True

    async def create_backup(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild_id, guild_name = interaction.guild_id, interaction.guild.name
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
            zip_filename = f"{database.sanitize_name(guild_name)}_manual_backup_{timestamp}.zip"
            db_paths = await database.get_all_db_paths_for_guild(guild_id, guild_name)
            if not db_paths:
                await interaction.followup.send("No database files found for this server.", ephemeral=True); return
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for db_path in db_paths:
                    if os.path.exists(db_path):
                        zipf.write(db_path, arcname=os.path.basename(db_path))
            zip_buffer.seek(0)
            await interaction.followup.send("Here is your server data backup:", file=discord.File(zip_buffer, filename=zip_filename), ephemeral=True)
        except Exception as e:
            logger.error(f"Error creating manual backup zip for guild {guild_id}: {e}", exc_info=True)
            await interaction.followup.send(f"An error occurred while creating the backup.", ephemeral=True)
    
    async def export_excel(self, interaction: Interaction):
        embed = discord.Embed(title="Choose Export Type", description=f"Please select the type of Excel export you want to generate.\n\n{EMOJIS['WARNING']} **Note:** The 'Detailed User Ledgers' option may take a while to generate for servers with many users and transactions.", color=COLORS["INFO"])
        view = ExportChoiceView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def clear_data(self, interaction: Interaction):
        embed = discord.Embed(title="⚠️ Clear Server Data", description="Select a data clearing option. **These actions are irreversible.**", color=COLORS["ERROR"])
        view = ClearDataView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)

    async def back(self, interaction: Interaction):
        from ..settings import SettingsMainView
        embed = discord.Embed(title=f"{EMOJIS['TOOL']} Bot Settings Panel", description="Select a category to configure.", color=COLORS["PRIMARY"])
        view = SettingsMainView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)