# cogs/lb.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import database
from utils.pagination import PaginationView
from utils.checks import actual_is_not_restricted_check, check_failure_error_handler
import logging
from utils.styles import COLORS, EMOJIS, format_currency, get_rank_emoji
import random

logger = logging.getLogger('cog.leaderboard')

class LeaderboardCog(commands.Cog, name="Leaderboard"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def format_leaderboard_page(self, page_items: list, current_page_num: int, total_pages: int, interaction: Interaction) -> discord.Embed:
        guild_name = interaction.guild.name if interaction.guild else "Unknown Server"
        
        # Choose a random trophy/decoration emoji
        decoration_emojis = [EMOJIS["TROPHY"], EMOJIS["SPARKLE"], EMOJIS["STAR"], EMOJIS["FIRE"]]
        decoration = random.choice(decoration_emojis)
        
        embed = discord.Embed(
            title=f"{decoration} {guild_name} Leaderboard {decoration}",
            color=COLORS["GOLD"]
        )
        
        if not page_items:
            embed.description = f"{EMOJIS['THINK']} No users found with a balance yet."
            return embed

        leaderboard_text = ""
        items_per_page = 10
        start_rank = (current_page_num - 1) * items_per_page + 1
        
        for i, user_data in enumerate(page_items):
            rank = start_rank + i
            user_id = user_data.get('user_id')
            display_name = user_data.get('user_name', f"User ID: {user_id}")
            balance = user_data.get('balance', 0.0)
            
            # Get appropriate rank emoji based on position
            rank_emoji = get_rank_emoji(rank)
            
            # Format with rank emoji and styled currency
            leaderboard_text += f"{rank_emoji} **#{rank}** {display_name}: **{format_currency(balance)}** {EMOJIS['COINS']}\n"

        embed.description = leaderboard_text
        embed.set_footer(text=f"Page {current_page_num}/{total_pages}")
        
        # Add a server icon if available
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        return embed

    @app_commands.command(name="lb", description="[Admin] View the server economy leaderboard.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(actual_is_not_restricted_check)
    async def lb(self, interaction: Interaction):
        if not interaction.guild:
            embed = discord.Embed(
                title=f"{EMOJIS['ALERT']} Error",
                description="This command can only be used in a server.",
                color=COLORS["ERROR"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        guild_id = interaction.guild_id
        guild_name = interaction.guild.name
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get the leaderboard data
            leaderboard_data = await database.get_leaderboard_data(guild_id, guild_name)
            
            if not leaderboard_data:
                embed = discord.Embed(
                    title=f"{EMOJIS['TROPHY']} {guild_name} Leaderboard",
                    description=f"{EMOJIS['THINK']} No users found with a balance yet.",
                    color=COLORS["GOLD"]
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
                
            # Create the pagination view
            pagination_view = PaginationView(
                interaction=interaction,
                all_items=leaderboard_data,
                items_per_page=10,
                page_formatter=self.format_leaderboard_page
            )
            
            # Send the initial message with the pagination view
            await pagination_view.send_initial_message(ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in /lb command (GID: {guild_id}): {e}", exc_info=True)
            
            embed = discord.Embed(
                title=f"{EMOJIS['ALERT']} Leaderboard Error",
                description=f"Sorry, I couldn't fetch the leaderboard data. Please try again later.",
                color=COLORS["ERROR"]
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @lb.error
    async def lb_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await check_failure_error_handler(interaction, error)

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
    logger.info("LeaderboardCog added to bot.")