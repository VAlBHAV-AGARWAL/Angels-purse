import discord
from discord import ui, Interaction, ButtonStyle
import logging
from typing import Optional

logger = logging.getLogger('utils.confirmation')

class ConfirmationView(ui.View):
    """
    A reusable confirmation view that provides confirm/cancel buttons for destructive operations.
    """
    def __init__(self, *, timeout: float = 60.0, user_id: int = None):
        super().__init__(timeout=timeout)
        self.value = None
        self.user_id = user_id  # If set, only this user can interact with the buttons
        self.message: Optional[discord.Message] = None
        
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Ensure only the original user can interact with this view if user_id is set"""
        if self.user_id is not None and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this confirmation.", ephemeral=True)
            return False
        return True
        
    @ui.button(label="Confirm", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Handle confirmation button press"""
        self.value = True
        self.stop()
        
        # Disable all buttons
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
                
        await interaction.response.edit_message(view=self)
        
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Handle cancel button press"""
        self.value = False
        self.stop()
        
        # Disable all buttons
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
                
        await interaction.response.edit_message(view=self)
    
    async def on_timeout(self):
        """Handle timeout - disable all buttons"""
        if self.message:
            for item in self.children:
                if isinstance(item, ui.Button):
                    item.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass
            except Exception as e:
                logger.warning(f"Error editing message on timeout: {e}")
        self.stop() 