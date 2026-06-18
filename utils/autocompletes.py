# utils/autocompletes.py
import discord
from discord import app_commands, Interaction
from typing import List
import database

async def context_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
    """
    A shared, smart autocomplete function for any command needing a work context.
    It dynamically shows channels or forum posts based on the server's settings.
    """
    if not interaction.guild:
        return []

    enabled_formats = await database.get_enabled_formats(interaction.guild_id, interaction.guild.name)
    choices = []

    # Add Text Channels if enabled
    if 'channel_based' in enabled_formats:
        for channel in interaction.guild.text_channels:
            if len(choices) >= 25: break
            if current.lower() in channel.name.lower():
                choices.append(app_commands.Choice(name=f"📁 #{channel.name}", value=str(channel.id)))

    # Add Forum Posts (Active and Archived) if one of the forum modes is enabled
    if 'forum_based' in enabled_formats or 'post_based' in enabled_formats:
        # First, get active threads
        for thread in interaction.guild.threads:
            if len(choices) >= 25: break
            if isinstance(thread.parent, discord.ForumChannel) and current.lower() in thread.name.lower():
                choices.append(app_commands.Choice(name=f"📝 {thread.parent.name}/{thread.name}", value=str(thread.id)))
        
        # Now, fetch archived threads from each forum
        for forum in interaction.guild.forums:
            if len(choices) >= 25: break
            try:
                async for thread in forum.archived_threads(limit=100):
                    if len(choices) >= 25: break
                    # Avoid adding duplicates if they were already found in active threads
                    if current.lower() in thread.name.lower() and not any(c.value == str(thread.id) for c in choices):
                        choices.append(app_commands.Choice(name=f"📝 {thread.parent.name}/{thread.name} (Archived)", value=str(thread.id)))
            except discord.Forbidden:
                continue  # Bot may not have permission

    return choices[:25]