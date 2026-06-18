# cogs/settings_views/assignment_view.py
import discord
from discord import ui, Interaction
from typing import List
import database
from utils.styles import COLORS, EMOJIS

class AssignmentSettingsView(ui.View):
    def __init__(self, original_interaction: Interaction, enabled_formats: List[str]):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.enabled_formats = enabled_formats
        self.update_button_styles()

    def update_button_styles(self):
        for child in self.children:
            if isinstance(child, ui.Button) and child.custom_id != "back_to_main":
                is_enabled = child.custom_id in self.enabled_formats
                child.style = discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.secondary
                child.label = f"{child.custom_id.replace('_', ' ').title()}"

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            return False
        return True

    async def toggle_format(self, interaction: Interaction, format_str: str):
        if format_str in self.enabled_formats:
            if len(self.enabled_formats) == 1:
                await interaction.response.send_message("You must have at least one assignment format enabled.", ephemeral=True)
                return
            self.enabled_formats.remove(format_str)
        else:
            self.enabled_formats.append(format_str)

        await database.set_enabled_formats(interaction.guild_id, interaction.guild.name, self.enabled_formats)
        self.update_button_styles()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(emoji="📁", custom_id="channel_based")
    async def channel_based(self, interaction: Interaction, button: ui.Button):
        await self.toggle_format(interaction, "channel_based")

    @ui.button(emoji="📖", custom_id="forum_based")
    async def forum_based(self, interaction: Interaction, button: ui.Button):
        await self.toggle_format(interaction, "forum_based")
        
    @ui.button(emoji="📝", custom_id="post_based")
    async def post_based(self, interaction: Interaction, button: ui.Button):
        await self.toggle_format(interaction, "post_based")

    @ui.button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=1, custom_id="back_to_main")
    async def back(self, interaction: Interaction, button: ui.Button):
        from ..settings import SettingsMainView
        embed = discord.Embed(title=f"{EMOJIS['TOOL']} Bot Settings Panel", description="Select a category to configure.", color=COLORS["PRIMARY"])
        view = SettingsMainView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)

    def create_embed(self) -> discord.Embed:
        descriptions = {
            "channel_based": "Transactions are linked to the Text Channel they are used in.",
            "forum_based": "Transactions are linked to the parent Forum of the post they are used in.",
            "post_based": "Transactions are linked to the specific Forum Post they are used in."
        }
        embed = discord.Embed(title="⚙️ Assignment Settings", description="Toggle which assignment formats are allowed. Green means ON.", color=COLORS["INFO"])
        status_lines = []
        for fmt in ["channel_based", "forum_based", "post_based"]:
            emoji = EMOJIS['CHECK'] if fmt in self.enabled_formats else EMOJIS['CROSS']
            status_lines.append(f"{emoji} **{fmt.replace('_', ' ').title()}** - {descriptions.get(fmt)}")
        embed.add_field(name="Enabled Formats", value="\n".join(status_lines), inline=False)
        return embed
