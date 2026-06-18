# cogs/settings_views/restriction_view.py (Final Version for Additive Permissions)
import discord
from discord import ui, Interaction
from typing import List
import database
from utils.styles import COLORS, EMOJIS

class ManageRolePermissionsView(ui.View):
    def __init__(self, original_interaction: Interaction, role: discord.Role, all_bot_commands: List[str]):
        super().__init__(timeout=300)
        self.original_interaction = original_interaction
        self.role = role
        self.all_bot_commands = sorted(all_bot_commands)
        self.allowed_commands = set()
        self.current_page = 0
        self.items_per_page = 20 # 4 rows of 5 buttons

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: Interaction):
        permissions = await database.get_command_restrictions_for_role(interaction.guild_id, interaction.guild.name, self.role.id)
        self.allowed_commands = {p['command_name'] for p in permissions if p['is_allowed']}
        self.update_components()
        embed = self.create_embed()
        
        # This interaction is from a component, so we must edit the original response
        await interaction.response.edit_message(embed=embed, view=self)

    def update_components(self):
        self.clear_items()
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        
        # Create a button for each command on the current page
        for command_name in self.all_bot_commands[start:end]:
            is_allowed = command_name in self.allowed_commands
            button = ui.Button(
                label=command_name,
                style=discord.ButtonStyle.success if is_allowed else discord.ButtonStyle.secondary,
                custom_id=f"toggle_cmd_{command_name}"
            )
            button.callback = self.create_callback(command_name)
            self.add_item(button)

        # Pagination controls
        total_pages = (len(self.all_bot_commands) + self.items_per_page - 1) // self.items_per_page
        page_controls_row = 4 # Place pagination on the last row
        if self.current_page > 0:
            self.add_item(self.PageButton("⬅️ Prev", -1, page_controls_row))
        if self.current_page < total_pages - 1:
            self.add_item(self.PageButton("Next ➡️", 1, page_controls_row))
        
        self.add_item(self.BackButton(page_controls_row))

    def create_embed(self) -> discord.Embed:
        total_pages = (len(self.all_bot_commands) + self.items_per_page - 1) // self.items_per_page
        embed = discord.Embed(
            title=f"🔒 Command Permissions for @{self.role.name}",
            description="Toggle which commands this role is **allowed** to use. Green means ON.",
            color=self.role.color if self.role.color.value != 0 else COLORS["PRIMARY"]
        )
        embed.set_footer(text=f"Page {self.current_page + 1}/{total_pages}")
        return embed

    def create_callback(self, command_name: str):
        async def callback(interaction: Interaction):
            is_currently_allowed = command_name in self.allowed_commands
            await database.set_command_restriction(interaction.guild_id, interaction.guild.name, self.role.id, command_name, not is_currently_allowed)
            # After updating the database, we need to refresh this view
            await self.refresh(interaction)
        return callback

    class PageButton(ui.Button):
        def __init__(self, label: str, direction: int, row: int):
            super().__init__(label=label, style=discord.ButtonStyle.grey, row=row)
            self.direction = direction
        async def callback(self, interaction: Interaction):
            self.view.current_page += self.direction
            await self.view.refresh(interaction)

    class BackButton(ui.Button):
        def __init__(self, row: int):
            super().__init__(label="⬅️ Back to Role Select", style=discord.ButtonStyle.grey, row=row)
        async def callback(self, interaction: Interaction):
            embed = discord.Embed(title="🔒 Restriction Management", description="Select a role from the dropdown to manage its command permissions.", color=COLORS["INFO"])
            view = RestrictionManagementView(self.view.original_interaction)
            await view.refresh(interaction)

class RestrictionManagementView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=300)
        self.original_interaction = original_interaction
        self.all_bot_commands = []

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: Interaction):
        self.all_bot_commands = sorted([cmd.name for cmd in self.original_interaction.client.tree.get_commands()])
        self.update_components(interaction.guild)
        embed = self.create_embed()
        
        # This view is the first one, so it edits the message from the main settings panel.
        await interaction.response.edit_message(embed=embed, view=self)

    def update_components(self, guild: discord.Guild):
        self.clear_items()
        
        role_options = [
            discord.SelectOption(label=f"@{role.name}", value=str(role.id))
            for role in sorted(guild.roles, key=lambda r: r.position, reverse=True) 
            if not role.managed and not role.is_default()
        ][:25]
        
        self.add_item(self.RoleSelect(role_options, "Manage permissions for a role..."))
        self.add_item(self.BackButton())

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔒 Restriction Management",
            description="By default, all roles are restricted from admin commands.\nSelect a role from the dropdown to grant it specific command permissions.",
            color=COLORS["INFO"]
        )
        return embed

    class RoleSelect(ui.Select):
        def __init__(self, options: List[discord.SelectOption], placeholder: str):
            super().__init__(options=options, placeholder=placeholder)
        
        async def callback(self, interaction: Interaction):
            role_id = int(self.values[0])
            role = interaction.guild.get_role(role_id)
            if not role:
                await interaction.response.send_message("Role not found.", ephemeral=True)
                return

            # Switch to the permission management view for the selected role
            view = ManageRolePermissionsView(self.view.original_interaction, role, self.view.all_bot_commands)
            await view.refresh(interaction)

    class BackButton(ui.Button):
        def __init__(self):
            super().__init__(label="⬅️ Back to Main Menu", style=discord.ButtonStyle.grey, row=1)
        async def callback(self, interaction: Interaction):
            from ..settings import SettingsMainView
            embed = discord.Embed(title=f"{EMOJIS['TOOL']} Bot Settings Panel", description="Select a category to configure.", color=COLORS["PRIMARY"])
            view = SettingsMainView(self.view.original_interaction)
            await interaction.response.edit_message(embed=embed, view=view)