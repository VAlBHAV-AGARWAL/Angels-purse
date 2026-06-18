# utils/checks.py (Final "Bot Settings are Supreme" Logic)
import discord
from discord import app_commands
import database
import logging
import os

logger = logging.getLogger(__name__)

try:
    BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', '0'))
except ValueError:
    BOT_OWNER_ID = 0

async def _is_user_restricted_logic(interaction: discord.Interaction) -> bool:
    """
    Checks if a user is restricted from using a command. This is the definitive check.
    Returns True if the user IS RESTRICTED, False otherwise.
    The bot's settings are the primary source of truth.
    """
    user = interaction.user
    guild = interaction.guild

    # --- NEW, SIMPLIFIED PERMISSION FLOW ---

    # Rule 1: Supreme Failsafes. Bot Owner and Server Owner are never restricted.
    if user.id == BOT_OWNER_ID:
        return False
    if guild and user.id == guild.owner_id:
        return False

    command_name = interaction.command.name if interaction.command else None
    if not command_name:
        return True # Should not happen, but restrict if command is unknown

    # Rule 2: Explicit Permission Grant.
    # Check all of the user's roles. If ANY role has been explicitly granted
    # permission for this specific command, the user is NOT restricted.
    if isinstance(user, discord.Member):
        user_role_ids = {role.id for role in user.roles}
        for role_id in user_role_ids:
            # This function checks the database for an "is_allowed = 1" entry.
            if await database.is_command_allowed_for_role(guild.id, guild.name, role_id, command_name):
                # An explicit "allow" was found. Access is granted.
                return False

    # Rule 3: Default to Deny.
    # If the user is not an owner and no explicit role permission was found,
    # they are RESTRICTED, regardless of their Discord permissions.
    return True

async def actual_is_not_restricted_check(interaction: discord.Interaction) -> bool:
    """The check decorator for slash commands. It passes if the user is NOT restricted."""
    return not await _is_user_restricted_logic(interaction)

async def user_is_restricted(interaction: discord.Interaction) -> bool:
    """Utility function for other parts of the code to check restriction status."""
    return await _is_user_restricted_logic(interaction)

async def check_failure_error_handler(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original_error = getattr(error, 'original', error)
    
    if isinstance(original_error, app_commands.CheckFailure):
        # We can now give a more specific message
        message_content = f"🚫 Access Denied. You need a role with permission for the `/{interaction.command.name}` command."
    elif isinstance(original_error, app_commands.MissingPermissions):
        message_content = "🚫 You lack the required Discord permissions for this command."
    else:
        command_name = interaction.command.name if interaction.command else "UnknownCmd"
        logger.error(f"Unhandled error in command '{command_name}': {error}", exc_info=True)
        message_content = "❗ An unexpected server error occurred."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message_content, ephemeral=True)
        else:
            await interaction.response.send_message(message_content, ephemeral=True)
    except discord.HTTPException:
        pass