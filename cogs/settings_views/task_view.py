# cogs/settings_views/task_view.py
import discord
from discord import ui, Interaction
from typing import List
import database
from utils.pagination import PaginationView
from utils.confirmation import ConfirmationView
from utils.styles import COLORS, EMOJIS

# Forward declare the main view to solve circular import
class SettingsMainView(ui.View):
    pass

class AddTaskModal(ui.Modal, title="Add or Update Task"):
    task_name = ui.TextInput(label="Task Name", placeholder="e.g., TYPESETTING", required=True, max_length=100)
    rank = ui.TextInput(label="Rank (Optional)", placeholder="e.g., 10 (lower numbers appear first)", required=False, max_length=5)

    async def on_submit(self, interaction: Interaction):
        if not interaction.guild_id or not interaction.guild:
            return
            
        task_name_upper = self.task_name.value.upper()
        rank_value = 0
        if self.rank.value and self.rank.value.isdigit():
            rank_value = int(self.rank.value)
        
        await database.add_task(interaction.guild_id, interaction.guild.name, task_name_upper, rank_value)
        embed = discord.Embed(
            title=f"{EMOJIS['CHECK']} Task Added/Updated",
            description=f"Task '**{discord.utils.escape_markdown(task_name_upper)}**' has been set with rank `{rank_value}`.",
            color=COLORS["SUCCESS"]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RemoveTaskView(ui.View):
    def __init__(self, original_interaction: Interaction, tasks: List[dict]):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.add_item(self.TaskSelect(tasks))

    @ui.button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=1)
    async def back_to_task_menu(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(title="📜 Task Management", description="Manage your server's tasks.", color=COLORS["INFO"])
        view = TaskManagementView(self.original_interaction)
        await interaction.response.edit_message(content=None, embed=embed, view=view)

    class TaskSelect(ui.Select):
        def __init__(self, tasks: List[dict]):
            options = [discord.SelectOption(label=t['task_name'], value=t['task_name']) for t in tasks[:25]]
            super().__init__(placeholder="Choose a task to remove...", options=options)

        async def callback(self, interaction: Interaction):
            if not interaction.guild_id or not interaction.guild:
                return
                
            task_name = self.values[0]
            confirm_view = ConfirmationView(user_id=interaction.user.id)
            confirm_embed = discord.Embed(title=f"{EMOJIS['WARNING']} Confirm Task Removal", 
                                       description=f"Are you sure you want to remove **{task_name}**?", 
                                       color=COLORS["WARNING"])
            await interaction.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
            await confirm_view.wait()
            if confirm_view.value:
                await database.remove_task(interaction.guild_id, interaction.guild.name, task_name)
                await database.delete_default_rate(interaction.guild_id, interaction.guild.name, task_name)
                await database.delete_channel_rates_for_task(interaction.guild_id, interaction.guild.name, task_name)
                await interaction.followup.send(f"Task **{task_name}** removed.", ephemeral=True)
            else:
                await interaction.followup.send("Task removal cancelled.", ephemeral=True)

class TaskManagementView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True

    @ui.button(label="Add/Update Task", style=discord.ButtonStyle.success, emoji="➕")
    async def add_task(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(AddTaskModal())

    @ui.button(label="Remove Task", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_task(self, interaction: Interaction, button: ui.Button):
        if not interaction.guild_id or not interaction.guild:
            return
            
        tasks = await database.get_tasks(interaction.guild_id, interaction.guild.name)
        if not tasks:
            await interaction.response.send_message("There are no tasks to remove.", ephemeral=True)
            return
        view = RemoveTaskView(self.original_interaction, tasks)
        await interaction.response.edit_message(content="Select a task to remove:", view=view)

    @ui.button(label="List All Tasks", style=discord.ButtonStyle.secondary, emoji="📋")
    async def list_tasks(self, interaction: Interaction, button: ui.Button):
        if not interaction.guild_id or not interaction.guild:
            return
            
        await interaction.response.defer()
        all_tasks = await database.get_tasks(interaction.guild_id, interaction.guild.name)
        if not all_tasks:
            await interaction.followup.send("No tasks defined yet.", ephemeral=True)
            return
        def format_page(items, page, total, _):
            embed = discord.Embed(title=f"{EMOJIS['SCROLL']} Task List - Page {page}/{total}", color=COLORS["TEAL"])
            embed.description = "\n".join([f"**{t['task_name']}** (Rank: {t['rank']})" for t in items])
            return embed
        pagination_view = PaginationView(interaction, all_tasks, 10, format_page)
        await pagination_view.send_initial_message(ephemeral=True)

    @ui.button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=1)
    async def back(self, interaction: Interaction, button: ui.Button):
        # We need to import the main view here to avoid circular imports at the top level
        from ..settings import SettingsMainView
        embed = discord.Embed(title=f"{EMOJIS['TOOL']} Bot Settings Panel", 
                            description="Select a category to configure.", 
                            color=COLORS["PRIMARY"])
        view = SettingsMainView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)
