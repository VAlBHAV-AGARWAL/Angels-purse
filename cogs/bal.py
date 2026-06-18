# cogs/bal.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import database
import logging
from datetime import datetime
from utils.styles import COLORS, EMOJIS, format_currency
import random

logger = logging.getLogger('cog.bal')

class BalanceCog(commands.Cog, name="Balance"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bal", description="Check your current balance.")
    @app_commands.guild_only()
    async def bal(self, interaction: Interaction):
        if not interaction.guild:
            embed = discord.Embed(
                title=f"{EMOJIS['ALERT']} Error",
                description="This command can only be used in a server.",
                color=COLORS["ERROR"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_id = interaction.user.id
        user_name = interaction.user.name
        guild_id = interaction.guild_id
        guild_name = interaction.guild.name

        await interaction.response.defer(ephemeral=True)
        try:
            # Update user's name in the database
            await database.update_user(guild_id, guild_name, user_id, user_name)
            
            # Get the user's balance
            current_balance = await database.get_balance(guild_id, guild_name, user_id, user_name)
            
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
                
            # Create a simple embed with just the balance
            embed = discord.Embed(
                title=f"{decoration} {balance_emoji} Your Balance {balance_emoji} {decoration}",
                description=f"**{interaction.user.mention}**, your current balance is:\n\n**{format_currency(current_balance)}** {EMOJIS['COINS']}",
                color=COLORS["GOLD"],
                timestamp=datetime.now()
            )
            
            # Set the user's avatar as the thumbnail if available
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in /bal (GID: {guild_id}) for user {user_id}: {e}", exc_info=True)
            
            embed = discord.Embed(
                title=f"{EMOJIS['ALERT']} Balance Error",
                description=f"Sorry {interaction.user.mention}, I couldn't fetch your balance. Please try again later.",
                color=COLORS["ERROR"]
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(BalanceCog(bot))