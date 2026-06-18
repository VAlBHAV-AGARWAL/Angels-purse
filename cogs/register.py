# cogs/register.py (Reverted to single /pay command)
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import database
import logging
import re
from utils.checks import check_failure_error_handler, actual_is_not_restricted_check
from utils.styles import COLORS, EMOJIS, format_currency
from datetime import datetime
import random

logger = logging.getLogger('cog.register')
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

class RegisterCog(commands.Cog, name="UserRegistration"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="register", description="Register or update your email and payment method.")
    @app_commands.guild_only()
    @app_commands.describe(email="Your email address.", payment_method="Your payment method and details.")
    async def register(self, interaction: Interaction, email: str, payment_method: app_commands.Range[str, 5, 200]):
        if not interaction.guild: return
        guild_id = interaction.guild_id
        guild_name = interaction.guild.name
        await interaction.response.defer(ephemeral=True)

        if not re.match(EMAIL_REGEX, email):
            embed = discord.Embed(
                title=f"{EMOJIS['ALERT']} Registration Error",
                description=f"{EMOJIS['CROSS']} Invalid email format.",
                color=COLORS["ERROR"]
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            await database.register_contact_info(guild_id, guild_name, interaction.user.id, interaction.user.name, email, payment_method)
            
            decoration = random.choice([EMOJIS["SPARKLE"], EMOJIS["STAR"], EMOJIS["MAGIC"]])
            
            embed = discord.Embed(
                title=f"{decoration} {EMOJIS['CHECK']} Registration Complete {decoration}",
                description=f"{EMOJIS['CHECK']} Your contact information has been updated!",
                color=COLORS["PINK"],
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name=f"{EMOJIS['MAIL']} Email", value=f"`{discord.utils.escape_markdown(email)}`", inline=False)
            embed.add_field(name=f"{EMOJIS['DOLLAR']} Payment Method", value=f"`{discord.utils.escape_markdown(payment_method)}`", inline=False)
            embed.set_footer(text=f"Registered by: {interaction.user.display_name}")
            
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in /register for user {interaction.user.id} GID {guild_id}: {e}", exc_info=True)
            embed = discord.Embed(
                title=f"{EMOJIS['ALERT']} Registration Error",
                description=f"{EMOJIS['SAD']} An error occurred while registering your information.",
                color=COLORS["ERROR"]
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="emails", description="[Admin] View a user's registered email.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(actual_is_not_restricted_check)
    @app_commands.describe(user="The user whose email to view.")
    async def emails(self, interaction: Interaction, user: discord.Member):
        if not interaction.guild: return
        if user.bot:
            embed = discord.Embed(
                title=f"{EMOJIS['ROBOT']} {EMOJIS['CROSS']} Error",
                description=f"Bots don't register emails.",
                color=COLORS["ERROR"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id, guild_name = interaction.guild_id, interaction.guild.name
        await interaction.response.defer(ephemeral=True)

        try:
            email_address = await database.get_user_email_by_id(guild_id, guild_name, user.id)
            if email_address:
                embed = discord.Embed(
                    title=f"{EMOJIS['MAIL']} Email Information for {user.display_name}",
                    color=COLORS["PINK"],
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Email", value=f"`{discord.utils.escape_markdown(email_address)}`", inline=False)
                if user.avatar: embed.set_thumbnail(url=user.avatar.url)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title=f"{EMOJIS['MAIL']} Email Information",
                    description=f"{EMOJIS['THINK']} {user.display_name} has not registered an email yet.",
                    color=COLORS["PINK"]
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in /emails for user {user.id} GID {guild_id}: {e}", exc_info=True)
            embed = discord.Embed(
                title=f"{EMOJIS['ALERT']} Email Lookup Error",
                description=f"{EMOJIS['SAD']} An error occurred while fetching email information.",
                color=COLORS["ERROR"]
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @emails.error
    async def emails_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await check_failure_error_handler(interaction, error)

    @app_commands.command(name="pay", description="[Admin] View a user's registered payment method.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(actual_is_not_restricted_check)
    @app_commands.describe(user="The user whose payment method to view.")
    async def pay(self, interaction: Interaction, user: discord.Member):
        if not interaction.guild: return
        if user.bot:
            await interaction.response.send_message("Bots don't have payment methods.", ephemeral=True)
            return

        guild_id, guild_name = interaction.guild_id, interaction.guild.name
        await interaction.response.defer(ephemeral=True)

        try:
            payment_details = await database.get_user_payment_method_by_id(guild_id, guild_name, user.id)
            if payment_details:
                embed = discord.Embed(
                    title=f"{EMOJIS['DOLLAR']} Payment Information for {user.display_name}",
                    color=COLORS["PINK"],
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Payment Method", value=f"`{discord.utils.escape_markdown(payment_details)}`", inline=False)
                if user.avatar: embed.set_thumbnail(url=user.avatar.url)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title=f"{EMOJIS['DOLLAR']} Payment Information",
                    description=f"{EMOJIS['THINK']} {user.display_name} has not registered a payment method yet.",
                    color=COLORS["PINK"]
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in /pay for user {user.id} GID {guild_id}: {e}", exc_info=True)
            await interaction.followup.send("An error occurred while fetching payment information.", ephemeral=True)
            
    @pay.error
    async def pay_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await check_failure_error_handler(interaction, error)

async def setup(bot: commands.Bot):
    await bot.add_cog(RegisterCog(bot))