# cogs/ping.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction # Ensure Interaction is imported
import time
import database
import logging
from utils.styles import COLORS, EMOJIS
import random

logger = logging.getLogger('cog.ping')

class PingCog(commands.Cog, name="Ping"):
    """Handles the ping command to check bot latency."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("PingCog loaded.")

    @app_commands.command(name="ping", description="Check the bot's responsiveness and latency.")
    async def ping(self, interaction: Interaction): # Corrected type hint
        """
        Calculates and displays different latencies:
        - Discord Gateway (WebSocket) latency.
        - Message Send/Edit (REST API) latency.
        - Database query latency.
        """
        time_before_defer = time.perf_counter()
        await interaction.response.defer(ephemeral=True)
        time_after_defer = time.perf_counter()
        defer_latency = (time_after_defer - time_before_defer) * 1000

        gateway_latency = self.bot.latency * 1000

        db_latency_economy = None
        
        guild_name_for_db = None # Initialize
        if interaction.guild: # Check if interaction is in a guild
            guild_name_for_db = interaction.guild.name

        if interaction.guild_id:
            try:
                # Pass guild_name_for_db, which can be None if not in a guild (though guild_id implies it is)
                db_latency_economy = await database.ping_db(interaction.guild_id, guild_name_for_db, db_type="economy")
            except Exception as e:
                logger.error(f"Error pinging databases for guild {interaction.guild_id}: {e}", exc_info=True)
                db_latency_economy = -1
        else: # DM context
            db_latency_economy = 0 # Or None, to indicate N/A more clearly

        # Choose a random ping emoji for fun
        ping_emojis = ["🏓", EMOJIS["CLOCK"], "📶", "⚡", "🚀"]
        ping_emoji = random.choice(ping_emojis)
        
        # Determine ping quality and color
        avg_latency = (gateway_latency + defer_latency) / 2
        if avg_latency < 100:
            latency_status = f"{EMOJIS['FIRE']} Blazing Fast!"
            embed_color = COLORS["EMERALD"]
        elif avg_latency < 200:
            latency_status = f"{EMOJIS['CHECK']} Great Speed!"
            embed_color = COLORS["SUCCESS"]
        elif avg_latency < 500:
            latency_status = f"{EMOJIS['COOL']} Good Speed"
            embed_color = COLORS["PRIMARY"]
        else:
            latency_status = f"{EMOJIS['THINK']} A Bit Slow"
            embed_color = COLORS["WARNING"]
        
        embed = discord.Embed(
            title=f"{ping_emoji} Pong! {ping_emoji}",
            description=f"**{latency_status}**",
            color=embed_color
        )
        
        embed.add_field(name=f"{EMOJIS['SPARKLE']} Gateway (WebSocket)", value=f"{gateway_latency:.2f} ms", inline=True)
        embed.add_field(name=f"{EMOJIS['ROBOT']} REST (Interaction)", value=f"{defer_latency:.2f} ms", inline=True)
        
        if db_latency_economy is not None:
            if db_latency_economy == -1:
                embed.add_field(name=f"{EMOJIS['CROSS']} DB Ping (Economy)", value="Error", inline=False)
            elif db_latency_economy == 0 and not interaction.guild_id: # Specifically for DM case
                 embed.add_field(name=f"{EMOJIS['BANK']} Database Ping", value="N/A (DM)", inline=False)
            else: # Valid latency or 0 in guild context (unlikely but possible)
                embed.add_field(name=f"{EMOJIS['BANK']} DB Ping (Economy)", value=f"{db_latency_economy:.2f} ms", inline=False)
        else: # If db_latency_economy remained None (e.g., ping_db returned None)
            embed.add_field(name=f"{EMOJIS['WARNING']} DB Ping (Economy)", value="N/A or Error", inline=False)

        footer_text = f"Requested by {interaction.user.display_name}"
        icon_url_footer = interaction.user.display_avatar.url if interaction.user.display_avatar else None
        embed.set_footer(text=footer_text, icon_url=icon_url_footer)
        embed.timestamp = discord.utils.utcnow()
        
        # Add some fun text based on ping quality
        if db_latency_economy and db_latency_economy > 0 and db_latency_economy < 100 and avg_latency < 150:
            embed.add_field(
                name=f"{EMOJIS['STAR']} Wow!", 
                value="Everything's running smoothly! The bot is feeling snappy today!", 
                inline=False
            )

        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.InteractionResponded:
            logger.warning("Attempted to followup.send on an already responded interaction in ping command.")
            try:
                original_response = await interaction.original_response()
                await original_response.edit(embed=embed)
            except Exception as e_edit:
                logger.error(f"Failed to edit original response in ping after followup failed: {e_edit}")
        except Exception as e:
            logger.error(f"Error sending ping followup: {e}", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PingCog(bot))