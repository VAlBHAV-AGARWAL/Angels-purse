# cogs/transaction_history.py (New Ledger Embed Design)
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
import database
from datetime import datetime
from utils.pagination import PaginationView
from utils import checks
from utils.autocompletes import context_autocomplete
import logging
from typing import Optional, Union, List
from utils.styles import COLORS, EMOJIS, format_currency
from utils.confirmation import ConfirmationView

logger = logging.getLogger('cog.trans_history')

class TransActionModal(ui.Modal, title="Select Transaction"):
    transaction_id = ui.TextInput(label="Transaction ID", placeholder="Enter the ID of the transaction...", required=True, min_length=1)

class EditReasonModal(ui.Modal, title="Edit Reason"):
    reason_input = ui.TextInput(label="New Reason", style=discord.TextStyle.paragraph, max_length=200)
    def __init__(self, current_reason: str):
        super().__init__()
        self.reason_input.default = current_reason
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()

class EditAmountModal(ui.Modal, title="Edit Amount"):
    amount_input = ui.TextInput(label="New Amount (must be a positive number)")
    def __init__(self, current_amount: float):
        super().__init__()
        self.amount_input.default = str(current_amount)
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()

class EditTaskModal(ui.Modal, title="Edit Task"):
    task_input = ui.TextInput(label="New Task Name")
    def __init__(self, current_task: str):
        super().__init__()
        self.task_input.default = current_task
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()

class TransactionEditView(ui.View):
    def __init__(self, original_interaction: Interaction, transaction_id: int):
        super().__init__(timeout=300)
        self.original_interaction = original_interaction
        self.transaction_id = transaction_id
        self.transaction_data = None
        self.message: Optional[discord.Message] = None
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True); return False
        return True
    async def update_view(self):
        gid = self.original_interaction.guild_id
        gname = self.original_interaction.guild.name
        self.transaction_data = await database.get_transaction_by_id(gid, gname, self.transaction_id)
        if not self.transaction_data:
            self.stop()
            if self.message: await self.message.edit(content="This transaction no longer exists.", embed=None, view=None)
            return
        embed = await self.create_embed()
        if self.message: await self.message.edit(embed=embed, view=self)
    async def create_embed(self) -> discord.Embed:
        if not self.transaction_data: return discord.Embed(title="Error", description="Could not load transaction data.", color=COLORS["ERROR"])
        guild = self.original_interaction.guild
        user_id, editor_id = self.transaction_data.get('user_id'), self.transaction_data.get('added_by_id')
        user_member = guild.get_member(user_id) if user_id and guild else None
        user_display = user_member.display_name if user_member else self.transaction_data.get('user_name', 'Unknown User')
        editor_member = guild.get_member(editor_id) if editor_id and guild else None
        editor_display = editor_member.display_name if editor_member else self.transaction_data.get('added_by_name', 'Unknown')
        context_str = "N/A"
        if self.transaction_data.get('post_id'): context_str = f"<#{self.transaction_data['post_id']}>"
        elif self.transaction_data.get('forum_id'): context_str = f"<#{self.transaction_data['forum_id']}>"
        elif self.transaction_data.get('channel_id'): context_str = f"<#{self.transaction_data['channel_id']}>"
        embed = discord.Embed(title=f"✏️ Editing Transaction ID: {self.transaction_id}", description="Click a button below to edit a specific field.", color=COLORS["PRIMARY"])
        embed.add_field(name="User", value=discord.utils.escape_markdown(user_display), inline=True)
        embed.add_field(name="Context", value=context_str, inline=True)
        embed.add_field(name="Amount", value=f"`{format_currency(self.transaction_data.get('amount', 0.0))}`", inline=True)
        embed.add_field(name="Task", value=f"`{self.transaction_data.get('task_name', 'N/A')}`", inline=False)
        embed.add_field(name="Reason", value=f"```{discord.utils.escape_markdown(self.transaction_data.get('reason', 'N/A'))}```", inline=False)
        embed.set_footer(text=f"Last action by: {editor_display} • This menu will time out.")
        return embed
    async def _handle_update(self, interaction: Interaction, **kwargs):
        kwargs['actor_id'], kwargs['actor_name'] = interaction.user.id, interaction.user.name
        await database.update_transaction(interaction.guild_id, interaction.guild.name, self.transaction_id, **kwargs)
        await self.update_view()
    @ui.button(label="Edit Amount", style=discord.ButtonStyle.secondary, emoji="💰")
    async def edit_amount(self, interaction: Interaction, button: ui.Button):
        modal = EditAmountModal(self.transaction_data.get('amount', 0.0))
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.amount_input.value is None: return
        try:
            new_amount = float(modal.amount_input.value)
            if new_amount <= 0:
                await interaction.followup.send("Amount must be a positive number.", ephemeral=True); return
            await self._handle_update(interaction, amount=new_amount)
        except (ValueError, TypeError):
            await interaction.followup.send("Invalid number format.", ephemeral=True)
    @ui.button(label="Edit Reason", style=discord.ButtonStyle.secondary, emoji="🗒️")
    async def edit_reason(self, interaction: Interaction, button: ui.Button):
        modal = EditReasonModal(self.transaction_data.get('reason', ''))
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.reason_input.value is None: return
        await self._handle_update(interaction, reason=modal.reason_input.value)
    @ui.button(label="Edit Task", style=discord.ButtonStyle.secondary, emoji="📜")
    async def edit_task(self, interaction: Interaction, button: ui.Button):
        modal = EditTaskModal(self.transaction_data.get('task_name', ''))
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.task_input.value is None: return
        task_upper = modal.task_input.value.upper()
        if not task_upper: await self._handle_update(interaction, task_name=None)
        elif not await database.get_task(interaction.guild_id, interaction.guild.name, task_upper):
            await interaction.followup.send(f"Task '{task_upper}' not found.", ephemeral=True); return
        else: await self._handle_update(interaction, task_name=task_upper)
    @ui.button(label="Done", style=discord.ButtonStyle.success, row=1)
    async def done(self, interaction: Interaction, button: ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Editing finished. You may need to refresh the ledger to see changes.", view=None, embed=None)

class LedgerView(PaginationView):
    def __init__(self, bot: commands.Bot, interaction: Interaction, all_items: list, items_per_page: int, page_formatter: callable, target_display: str, show_admin_buttons: bool = False):
        super().__init__(interaction, all_items, items_per_page, page_formatter)
        self.bot, self.target_display = bot, target_display
        if show_admin_buttons: self.add_item(self.EditButton()); self.add_item(self.DeleteButton())
    class EditButton(ui.Button):
        def __init__(self):
            super().__init__(label="Edit Entry", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
        async def callback(self, interaction: Interaction):
            class IdModal(ui.Modal, title="Edit Transaction"):
                transaction_id_input = ui.TextInput(label="Transaction ID", placeholder="Enter the ID of the transaction to edit...")
                async def on_submit(self, modal_interaction: discord.Interaction):
                    await modal_interaction.response.defer(ephemeral=True, thinking=True)
                    try:
                        tid = int(self.transaction_id_input.value)
                        tx = await database.get_transaction_by_id(modal_interaction.guild_id, modal_interaction.guild.name, tid)
                        if not tx: await modal_interaction.followup.send(f"Transaction ID `{tid}` not found.", ephemeral=True); return
                        edit_view = TransactionEditView(interaction, tid)
                        await edit_view.update_view()
                        message = await modal_interaction.followup.send(embed=await edit_view.create_embed(), view=edit_view, ephemeral=True)
                        edit_view.message = message
                    except ValueError: await modal_interaction.followup.send("Invalid Transaction ID. Please enter a number.", ephemeral=True)
                    except Exception as e:
                        logger.error(f"Error in transaction edit modal: {e}", exc_info=True)
                        await modal_interaction.followup.send("An unexpected error occurred.", ephemeral=True)
            await interaction.response.send_modal(IdModal())
    class DeleteButton(ui.Button):
        def __init__(self):
            super().__init__(label="Delete Entry", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
        async def callback(self, interaction: Interaction):
            modal = TransActionModal(title="Delete Transaction")
            await interaction.response.send_modal(modal)
            await modal.wait()
            if not modal.transaction_id.value: return
            try:
                tid = int(modal.transaction_id.value)
                gid, gname = interaction.guild_id, interaction.guild.name
                if not await database.get_transaction_by_id(gid, gname, tid):
                    await interaction.followup.send(f"Transaction ID `{tid}` not found.", ephemeral=True); return
                confirm_view = ConfirmationView(user_id=interaction.user.id)
                await interaction.followup.send(f"Are you sure you want to permanently delete transaction `{tid}`?", view=confirm_view, ephemeral=True)
                await confirm_view.wait()
                if confirm_view.value:
                    await database.delete_transaction(gid, gname, tid)
                    await interaction.followup.send(f"🗑️ Transaction `{tid}` has been deleted. You may need to refresh the ledger to see changes.", ephemeral=True)
                else: await interaction.followup.send("Deletion cancelled.", ephemeral=True)
            except ValueError: await interaction.followup.send("Invalid Transaction ID.", ephemeral=True)

class TransactionHistoryCog(commands.Cog, name="TransactionHistory"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    def _format_ledger_page(self, page_items: list, page: int, total: int, target: str, inter: Interaction) -> discord.Embed:
        embed = discord.Embed(title=f"📖 Ledger: {target}", color=COLORS["PRIMARY"])
        
        lines = []
        for trans in page_items:
            tid = trans.get('transaction_id')
            amt = trans.get('amount', 0.0)
            ttype = trans.get('type', 'N/A').capitalize()
            rsn = trans.get('reason', 'N/A')
            ts_str = trans.get('timestamp')
            task = trans.get('task_name', 'N/A')
            
            # Fetch user's server nickname (display name)
            user_id = trans.get('user_id')
            member = inter.guild.get_member(user_id) if inter.guild and user_id else None
            user_display_name = member.display_name if member else trans.get('user_name', 'Unknown User')

            # Fetch actor's server nickname (display name)
            actor_id = trans.get('added_by_id')
            actor_member = inter.guild.get_member(actor_id) if inter.guild and actor_id else None
            actor_display_name = actor_member.display_name if actor_member else trans.get('added_by_name', 'Unknown')

            try:
                dt = datetime.fromisoformat(ts_str)
                date_str = dt.strftime("%d %B %Y")
            except:
                date_str = "Unknown Date"

            # Determine emoji based on transaction type
            type_emoji = EMOJIS['ADD'] if ttype == 'Add' else EMOJIS['REMOVE']
            
            # Format the amount string with backticks
            amount_str = f"`{'+' if ttype == 'Add' else '-'}${abs(amt):,.2f}`"

            # Format the context string as a clickable link
            context_str = "N/A"
            if trans.get('post_id'): context_str = f"<#{trans['post_id']}>"
            elif trans.get('forum_id'): context_str = f"<#{trans['forum_id']}>"
            elif trans.get('channel_id'): context_str = f"<#{trans['channel_id']}>"

            # Build the main line
            main_line = (
                f"{type_emoji} {amount_str} | `{task}` | **{discord.utils.escape_markdown(user_display_name)}** | "
                f"{context_str} | *For `{discord.utils.escape_markdown(rsn)}`*"
            )

            # Build the indented footer line
            footer_line = f"└ `ID: {tid} | {date_str} | By: {discord.utils.escape_markdown(actor_display_name)}`"
            
            # Combine them
            entry_block = f"{main_line}\n{footer_line}"
            lines.append(entry_block)

        embed.description = "\n\n".join(lines) if lines else "No transactions found on this page."
        embed.set_footer(text=f"Page {page}/{total}")
        return embed
    @app_commands.command(name="ledger", description="View, edit, or delete transaction history.")
    @app_commands.guild_only()
    @app_commands.describe(user="View a user's ledger.", context="View a channel or post's ledger.")
    @app_commands.autocomplete(context=context_autocomplete)
    async def ledger(self, interaction: Interaction, user: Optional[discord.Member] = None, context: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        gid, gname, req_user = interaction.guild_id, interaction.guild.name, interaction.user
        target_disp, user_id_filter, context_id_filter = "", None, None
        if user and context: await interaction.followup.send("Please specify a user OR a context, not both.", ephemeral=True); return
        show_admin_buttons = req_user.guild_permissions.administrator and not await checks.user_is_restricted(interaction)
        is_admin = req_user.guild_permissions.administrator
        target_context_obj = None
        if context:
            try:
                context_id = int(context)
                target_context_obj = interaction.guild.get_channel_or_thread(context_id)
                if target_context_obj is None: target_context_obj = await interaction.guild.fetch_channel(context_id)
            except (ValueError, discord.NotFound, discord.Forbidden): await interaction.followup.send("Invalid context selected or I can't see that channel/post.", ephemeral=True); return
        if user:
            if user.id != req_user.id and (not is_admin or await checks.user_is_restricted(interaction)): await interaction.followup.send("You do not have permission to view another user's ledger.", ephemeral=True); return
            target_disp = f"for {user.display_name}"; user_id_filter = user.id
        else:
            if not context: target_context_obj = interaction.channel
            if not target_context_obj: await interaction.followup.send("You must be in a channel or specify a context to view its ledger.", ephemeral=True); return
            if not is_admin or await checks.user_is_restricted(interaction): await interaction.followup.send("You do not have permission to view a context's ledger.", ephemeral=True); return
            enabled_formats = await database.get_enabled_formats(gid, gname)
            if 'forum_based' in enabled_formats and isinstance(target_context_obj, discord.Thread) and isinstance(target_context_obj.parent, discord.ForumChannel):
                context_id_filter, target_disp = target_context_obj.parent.id, f"for forum '{target_context_obj.parent.name}'"
            else: context_id_filter, target_disp = target_context_obj.id, f"for {target_context_obj.mention}"
        all_tx = await database.get_transactions(gid, gname, user_id=user_id_filter, context_id=context_id_filter, limit=None)
        if not all_tx: await interaction.followup.send(f"No transactions found {target_disp}.", ephemeral=True); return
        formatter = lambda items, page, total, inter: self._format_ledger_page(items, page, total, target_disp, inter)
        view = LedgerView(self.bot, interaction, all_tx, 5, formatter, target_disp, show_admin_buttons=show_admin_buttons)
        await view.send_initial_message(ephemeral=True)
    @ledger.error
    async def ledger_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await checks.check_failure_error_handler(interaction, error)

async def setup(bot: commands.Bot):
    cog_name = "TransactionHistory"
    if bot.get_cog(cog_name) is None:
        await bot.add_cog(TransactionHistoryCog(bot))
        logging.getLogger('cog.trans_history').info(f"{cog_name} cog loaded.")
    else:
        logging.getLogger('cog.trans_history').warning(f"Attempted to load {cog_name} cog, but it was already loaded. Skipping.")