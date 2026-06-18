# cogs/report.py (Final version with 3 buttons and working support link)
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
import logging
import os
from utils.styles import COLORS, EMOJIS

logger = logging.getLogger('cog.report')

BOT_OWNER_ID_STR = os.getenv('BOT_OWNER_ID')
SUPPORT_SERVER_INVITE = os.getenv('BOT_SUPPORT_SERVER_INVITE')

class ReportFollowUpView(ui.View):
    """The view with three follow-up options presented to the user."""
    def __init__(self, bot: commands.Bot, owner_id: int, report_embed: discord.Embed):
        super().__init__(timeout=300)
        self.bot = bot
        self.owner_id = owner_id
        self.report_embed = report_embed
        self.owner: discord.User = None
        self.action_taken = False
        
        # Disable the "Join Server" button if no invite link is configured in .env
        if not SUPPORT_SERVER_INVITE:
            # The button is now the second child (index 1)
            join_server_button = self.children[1] 
            if isinstance(join_server_button, ui.Button):
                join_server_button.disabled = True
                join_server_button.label = "Support Server (None)"

    async def send_report_to_owner(self, interaction: Interaction, contact_info: str):
        """Helper function to format and send the final report to the owner."""
        if self.action_taken:
            await interaction.response.defer()
            return
        self.action_taken = True

        if not self.owner:
            try:
                self.owner = await self.bot.fetch_user(self.owner_id)
            except discord.NotFound:
                await interaction.response.edit_message(content=f"{EMOJIS['CROSS']} Error: Could not find the bot owner.", view=None, embed=None)
                return

        self.report_embed.add_field(name="Follow-Up Action", value=contact_info, inline=False)
        
        try:
            await self.owner.send(embed=self.report_embed)
            # The confirmation message is now handled within each button's callback
        except discord.Forbidden:
            await interaction.response.edit_message(content=f"{EMOJIS['CROSS']} I couldn't DM the bot owner. The report was not sent.", view=None, embed=None)
        except Exception as e:
            logger.error(f"Failed to send final report DM: {e}")
            await interaction.response.edit_message(content=f"{EMOJIS['CROSS']} An error occurred while sending the final report.", view=None, embed=None)

    @ui.button(label="Invite Owner to Server", style=discord.ButtonStyle.secondary, emoji="✉️", row=0)
    async def invite_owner(self, interaction: Interaction, button: ui.Button):
        contact_info = "User requested an invite to their server for follow-up."
        if interaction.channel and isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            try:
                invite = await interaction.channel.create_invite(max_age=86400, max_uses=1, reason="Bot report follow-up")
                contact_info += f"\n**Server Invite:** {invite.url}"
            except discord.Forbidden:
                contact_info += "\n*Bot lacked permissions to create an invite.*"
        else:
            contact_info += "\n*Could not create invite (not in a valid server channel).*"
        
        # Await the report sending first
        await self.send_report_to_owner(interaction, contact_info)
        # Then edit the original message with the confirmation
        if not self.action_taken: return # Don't send confirmation if report failed
        await interaction.response.edit_message(content=f"{EMOJIS['CHECK']} Thank you! Your report has been sent.", view=None, embed=None)


    # --- THIS IS THE CORRECTED BUTTON ---
    @ui.button(label="Join Support Server", style=discord.ButtonStyle.secondary, emoji="🏠", row=0)
    async def join_server(self, interaction: Interaction, button: ui.Button):
        contact_info = "User was provided with the support server invite."
        
        # Send the report to the owner *first*
        await self.send_report_to_owner(interaction, contact_info)
        
        if not self.action_taken: return # Don't proceed if sending the report failed
        
        # Now, respond to the user with the actual link
        response_message = (
            f"{EMOJIS['CHECK']} Thank you! Your report has been sent.\n\n"
            f"Here is the link to the support server:\n{SUPPORT_SERVER_INVITE}"
        )
        await interaction.response.edit_message(content=response_message, view=None, embed=None)

    # The "Open a DM" button has been completely removed.

    @ui.button(label="No Follow-up Needed", style=discord.ButtonStyle.grey, emoji="👍", row=1)
    async def no_follow_up(self, interaction: Interaction, button: ui.Button):
        contact_info = "User specified that no follow-up is needed."

        await self.send_report_to_owner(interaction, contact_info)
        
        if not self.action_taken: return # Don't send confirmation if report failed
        await interaction.response.edit_message(content=f"{EMOJIS['CHECK']} Thank you! Your report has been sent.", view=None, embed=None)


class ReportCog(commands.Cog, name="Report"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.owner_id_int: int | None = None
        if BOT_OWNER_ID_STR:
            try:
                self.owner_id_int = int(BOT_OWNER_ID_STR)
            except ValueError:
                logger.error("BOT_OWNER_ID is not a valid integer. Report command is disabled.")
        else:
            logger.warning("BOT_OWNER_ID not found in .env. Report command is disabled.")
        logger.info("ReportCog loaded.")

    @app_commands.command(name="report", description="Report an issue or bug to the bot owner.")
    @app_commands.describe(message="Your report message. Please be as detailed as possible.")
    async def report(self, interaction: Interaction, message: app_commands.Range[str, 10, 1000]):
        if not self.owner_id_int:
            await interaction.response.send_message("The report system is not configured.", ephemeral=True)
            return

        # Build the initial report embed
        embed = discord.Embed(
            title=f"{EMOJIS['WARNING']} New Bot Report",
            description=message,
            color=COLORS["ORANGE"],
            timestamp=discord.utils.utcnow()
        )
        guild_name = interaction.guild.name if interaction.guild else "Direct Message"
        embed.add_field(name="Reporter", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=False)
        embed.add_field(name="Source Server", value=f"{guild_name} (ID: {interaction.guild_id})", inline=True)
        if interaction.channel:
            embed.add_field(name="Source Context", value=f"#{interaction.channel.name} (ID: {interaction.channel.id})", inline=True)
        if interaction.user.display_avatar:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # Send the follow-up prompt to the user
        follow_up_embed = discord.Embed(
            title="Report Sent",
            description="Your report has been received. Please choose a follow-up option below if needed.",
            color=COLORS["SUCCESS"]
        )
        view = ReportFollowUpView(self.bot, self.owner_id_int, embed)
        await interaction.response.send_message(embed=follow_up_embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReportCog(bot))