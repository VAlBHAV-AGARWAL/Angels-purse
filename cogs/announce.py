# cogs/announce.py (Using a Modal for the message)
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
import logging
import asyncio
import os
from utils.styles import COLORS, EMOJIS

logger = logging.getLogger('cog.announce')

DEV_GUILD_ID = os.getenv('DEV_GUILD_ID')
if DEV_GUILD_ID:
    DEV_GUILD = discord.Object(id=int(DEV_GUILD_ID))
else:
    DEV_GUILD = None

# --- NEW: A Modal for typing the announcement ---
class NoticeModal(ui.Modal, title="Broadcast Announcement"):
    message_input = ui.TextInput(
        label="Announcement Message",
        style=discord.TextStyle.paragraph, # This creates a large text box
        placeholder="Type your multi-line announcement here. Markdown is supported.",
        required=True,
        max_length=1500 # Generous length for an embed description
    )

    async def on_submit(self, interaction: Interaction):
        # We will do all the work here after the modal is submitted.
        # This keeps the logic clean and responds to the correct interaction.
        await interaction.response.defer(ephemeral=True, thinking=True)

        bot = interaction.client
        message = self.message_input.value

        embed = discord.Embed(
            title=f"{EMOJIS['ALERT']} A Notice from the Bot Developer",
            description=message,
            color=COLORS["PINK"],
            timestamp=discord.utils.utcnow()
        )
        if bot.user.avatar:
            embed.set_footer(text=f"Sent by {bot.user.name}", icon_url=bot.user.avatar.url)

        success_count = 0
        fail_count = 0
        failed_guilds = []

        for guild in bot.guilds:
            if guild.owner:
                try:
                    await guild.owner.send(embed=embed)
                    success_count += 1
                except discord.Forbidden:
                    fail_count += 1
                    failed_guilds.append(f"`{guild.name}`")
            else:
                fail_count += 1
                failed_guilds.append(f"`{guild.name}` (Owner not found)")
            
            await asyncio.sleep(0.5) # A slightly shorter sleep is fine

        summary_embed = discord.Embed(
            title="Announcement Broadcast Report",
            color=COLORS["SUCCESS"] if fail_count == 0 else COLORS["WARNING"],
            timestamp=discord.utils.utcnow()
        )
        summary_embed.add_field(name="Messages Sent Successfully", value=str(success_count), inline=True)
        summary_embed.add_field(name="Messages Failed", value=str(fail_count), inline=True)
        
        if failed_guilds:
            summary_embed.add_field(name="Failed Servers", value=", ".join(failed_guilds)[:1024], inline=False)
            
        await interaction.followup.send(embed=summary_embed, ephemeral=True)


class AnnounceCog(commands.Cog, name="BotAnnouncements"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- THE COMMAND IS NOW SIMPLER ---
    @app_commands.command(name="notice", description="[Bot Owner] Opens a popup to send an announcement to all server owners.")
    @commands.is_owner()
    @app_commands.guilds(DEV_GUILD) if DEV_GUILD else app_commands.rename()
    async def notice(self, interaction: Interaction):
        """Opens a modal to type and send a broadcast message."""
        # The command's only job is to show the modal.
        await interaction.response.send_modal(NoticeModal())

    # Error handler is unchanged
    @notice.error
    async def notice_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, commands.NotOwner):
            await interaction.response.send_message("🚫 This is a developer-only command.", ephemeral=True)
        else:
            logger.error(f"An error occurred in the /notice command: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

async def setup(bot: commands.Bot):
    if DEV_GUILD:
        await bot.add_cog(AnnounceCog(bot))
    else:
        logger.warning("Skipping load of AnnounceCog because DEV_GUILD_ID is not set in .env.")