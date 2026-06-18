# cogs/balance.py (Admin command to check other's balance)
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import database
from utils.checks import actual_is_not_restricted_check, check_failure_error_handler
import logging
from datetime import datetime
from utils.styles import COLORS, EMOJIS, format_currency
import random

logger = logging.getLogger('cog.admin_balance')

class AdminBalanceCog(commands.Cog, name="AdminBalance"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="[Admin] Check a specific user's balance.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(actual_is_not_restricted_check)
    @app_commands.describe(user="The user whose balance you want to check.")
    async def balance(self, interaction: Interaction, user: discord.Member):
        if not interaction.guild:
            try:
                embed = discord.Embed(
                    title=f"{EMOJIS['ALERT']} Error",
                    description="This command can only be used in a server.",
                    color=COLORS["ERROR"]
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                logger.error(f"Error responding to guild check in balance command: {e}")
            return
            
        if user.bot:
            try:
                embed = discord.Embed(
                    title=f"{EMOJIS['ROBOT']} {EMOJIS['CROSS']} Error",
                    description=f"Bots don't have balances, silly!",
                    color=COLORS["ERROR"]
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                logger.error(f"Error responding to bot check in balance command: {e}")
            return

        guild_id = interaction.guild_id
        guild_name = interaction.guild.name

        try:
            await interaction.response.defer(ephemeral=True)
            
            # Update username in database
            await database.update_user(guild_id, guild_name, user.id, user.display_name)
            
            # Get balance for this user
            current_balance = await database.get_balance(guild_id, guild_name, user.id, user.name)
            
            # Pick an appropriate emoji based on balance
            balance_emoji = EMOJIS["WALLET"]
            if current_balance > 1000:
                balance_emoji = EMOJIS["MONEY"]
            if current_balance > 5000:
                balance_emoji = EMOJIS["RICH"]
            if current_balance > 10000:
                balance_emoji = EMOJIS["GEM"]
                
            # Pick a random decoration emoji
            decoration = random.choice([EMOJIS["SPARKLE"], EMOJIS["STAR"], EMOJIS["FIRE"]])
            
            # Create a simple embed
            embed = discord.Embed(
                title=f"{decoration} {balance_emoji} {user.display_name}'s Balance {balance_emoji} {decoration}",
                description=f"Current balance: **{format_currency(current_balance)}** {EMOJIS['COINS']}",
                color=COLORS["GOLD"],
                timestamp=datetime.now()
            )
            
            # Set the user's avatar as the thumbnail if available
            if user.avatar:
                embed.set_thumbnail(url=user.avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.NotFound as e:
            # Handle unknown interaction error
            logger.warning(f"Interaction not found in balance command: {e}")
        except discord.errors.HTTPException as e:
            logger.error(f"HTTP error in balance command: {e}")
        except Exception as e:
            logger.error(f"Error in admin /balance (GID: {guild_id}) for user {user.id}: {e}", exc_info=True)
            try:
                embed = discord.Embed(
                    title=f"{EMOJIS['ALERT']} Balance Error",
                    description=f"Sorry, couldn't fetch balance for {user.mention}.",
                    color=COLORS["ERROR"]
                )
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass  # Ignore followup errors if interaction already failed

    @balance.error
    async def balance_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await check_failure_error_handler(interaction, error)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminBalanceCog(bot))