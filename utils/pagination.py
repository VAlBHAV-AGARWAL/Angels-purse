# utils/pagination.py
import discord
from discord import ui # Using discord.ui for modern views
import logging
from typing import List, Any, Callable, Optional, Coroutine

logger = logging.getLogger('discord_bot_pagination')

class JumpToPageModal(ui.Modal, title='Jump to Page'):
    """A modal for users to input a page number to jump to."""
    page_input = ui.TextInput(
        label='Page Number',
        placeholder='Enter the page number you want to go to...',
        required=True,
        min_length=1,
        max_length=5 # Max 99999 pages, adjust if needed
    )

    def __init__(self, max_pages: int, current_page_callback: Callable[[int], Coroutine[Any, Any, None]]):
        super().__init__(timeout=120) # Modal timeout
        self.max_pages = max_pages
        self.current_page_callback = current_page_callback # Callback to update the view to the new page

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page_num = int(self.page_input.value)
            if 1 <= page_num <= self.max_pages:
                # The callback should handle interaction response/deferral if it edits the message
                # The callback receives 0-indexed page
                await self.current_page_callback(page_num - 1) 
                # If the callback doesn't respond to interaction, we might need to do it here.
                # However, typical pattern is callback edits the message, fulfilling interaction.
                if not interaction.response.is_done():
                    # This might happen if callback is very fast and doesn't edit,
                    # or if it's a fire-and-forget.
                    # For safety, let's ensure the modal interaction is acknowledged.
                    await interaction.response.defer(ephemeral=True, thinking=False) # Invisible ack
            else:
                await interaction.response.send_message(
                    f"Invalid page number. Please enter a number between 1 and {self.max_pages}.",
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message(
                "Invalid input. Please enter a valid number.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in JumpToPageModal on_submit: {e}", exc_info=True)
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message("An error occurred processing your request.", ephemeral=True)
                except discord.InteractionResponded: # Should not happen if not is_done()
                    pass # Response already sent by some other path.


class PaginationView(ui.View):
    """
    A view for paginating through a list of items and displaying them in an embed.
    Manages navigation buttons (first, previous, jump, next, last).
    """
    def __init__(self,
                 interaction: discord.Interaction,
                 all_items: List[Any],
                 items_per_page: int,
                 page_formatter: Callable[[List[Any], int, int, discord.Interaction], discord.Embed],
                 timeout: Optional[float] = 180.0,
                 dynamic_loader: Optional[Callable[[int, int], Coroutine[Any, Any, List[Any]]]] = None,
                 total_items: int = None):
        """
        Initialize a pagination view.
        
        Parameters:
        - interaction: The original command interaction
        - all_items: Initial list of items to paginate
        - items_per_page: Number of items to show per page
        - page_formatter: Function to format items into an embed
        - timeout: View timeout in seconds
        - dynamic_loader: Optional async function that loads items on demand when a page is accessed
                          Should accept (page_num, page_size) and return a list of items
        - total_items: Only used with dynamic_loader, specifies the total number of items
                       if known but not all loaded (for accurate page count)
        """
        super().__init__(timeout=timeout)
        self.interaction_owner_id = interaction.user.id # Store owner ID for interaction_check
        self.original_interaction = interaction # Store original interaction for formatter if needed
        self.all_items = all_items
        self.items_per_page = items_per_page
        self.page_formatter = page_formatter 
        self.current_page = 0 
        self.dynamic_loader = dynamic_loader
        
        # Calculate total pages based on total_items if provided, otherwise use length of all_items
        if dynamic_loader and total_items is not None:
            self.total_items = total_items
            self.total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        else:
            self.total_items = len(self.all_items)
            self.total_pages = (self.total_items + self.items_per_page - 1) // self.items_per_page
            
        if self.total_pages == 0: self.total_pages = 1 # Ensure at least 1 page even if no items, to show "no data"
        self.message: Optional[discord.Message] = None 
        
        # Keep track of loaded pages for dynamic loading
        self.loaded_pages = {0: all_items[:items_per_page]} if dynamic_loader else {}

        self._update_button_states()

    def _update_button_states(self):
        """Disables/enables navigation buttons based on the current page."""
        # Check if buttons have been added to the view (i.e., are attributes)
        first_page_button = getattr(self, 'first_page_button', None)
        prev_page_button = getattr(self, 'prev_page_button', None)
        next_page_button = getattr(self, 'next_page_button', None)
        last_page_button = getattr(self, 'last_page_button', None)
        jump_to_page_button = getattr(self, 'jump_to_page_button', None)

        if first_page_button: first_page_button.disabled = (self.current_page == 0)
        if prev_page_button: prev_page_button.disabled = (self.current_page == 0)
        if next_page_button: next_page_button.disabled = (self.current_page >= self.total_pages - 1)
        if last_page_button: last_page_button.disabled = (self.current_page >= self.total_pages - 1)
        if jump_to_page_button: jump_to_page_button.disabled = (self.total_pages <= 1)

    async def get_page_items(self, page_num: int) -> List[Any]:
        """Get items for the specified page, either from cache or by loading dynamically."""
        if not self.dynamic_loader:
            # If not using dynamic loading, slice from all_items
            start_index = page_num * self.items_per_page
            end_index = start_index + self.items_per_page
            return self.all_items[start_index:end_index]
        
        # Using dynamic loading, check if page is cached
        if page_num in self.loaded_pages:
            return self.loaded_pages[page_num]
        
        try:
            # Load the page data dynamically
            items = await self.dynamic_loader(page_num + 1, self.items_per_page)
            # Cache the loaded items
            self.loaded_pages[page_num] = items
            return items
        except Exception as e:
            logger.error(f"Error loading page {page_num} dynamically: {e}", exc_info=True)
            return []  # Return empty list on error

    def get_current_page_embed(self) -> discord.Embed:
        """Gets the items for the current page and formats them into an embed."""
        if self.dynamic_loader:
            # For dynamic loading, we need to wait for the items
            # This is async, but we can't use async here, so just return a placeholder
            # The actual loading happens in update_message
            return discord.Embed(title="Loading...", description="Please wait while the content loads...")
        else:
            # For non-dynamic loading, get items directly
            start_index = self.current_page * self.items_per_page
            end_index = start_index + self.items_per_page
            page_items = self.all_items[start_index:end_index]
            return self.page_formatter(page_items, self.current_page + 1, self.total_pages, self.original_interaction)

    async def update_message(self, interaction_for_ack: Optional[discord.Interaction] = None):
        """Updates the existing message with the current page. Optionally acks a new interaction."""
        # Get items for the current page, handling dynamic loading if needed
        if self.dynamic_loader:
            page_items = await self.get_page_items(self.current_page)
            embed = self.page_formatter(page_items, self.current_page + 1, self.total_pages, self.original_interaction)
        else:
            embed = self.get_current_page_embed()
            
        self._update_button_states()
        
        if interaction_for_ack and not interaction_for_ack.response.is_done():
            await interaction_for_ack.response.edit_message(embed=embed, view=self)
        elif self.message: # Fallback to editing the stored message if no interaction_for_ack or it's done
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.NotFound:
                logger.warning("Pagination message not found for editing, view might have timed out or message deleted.")
                self.stop()
            except discord.HTTPException as e:
                logger.error(f"HTTPException editing pagination message: {e}", exc_info=True)
                # self.stop() # Maybe don't stop for all HTTP errors, could be rate limits
        else: # No message to edit and no interaction to respond to. Should not happen.
            logger.error("PaginationView.update_message called with no message and no interaction_for_ack.")

    async def send_initial_message(self, ephemeral: bool = True):
        """Sends the first page as a new message or followup."""
        if (not self.all_items and self.total_pages <= 1 and not self.dynamic_loader) or (self.dynamic_loader and self.total_items == 0): 
            # Show no data if truly empty
            embed = discord.Embed(description="There is no data to display.", color=discord.Color.orange())
            if self.original_interaction.response.is_done():
                self.message = await self.original_interaction.followup.send(embed=embed, view=self if self.total_pages > 1 else None, ephemeral=ephemeral)
            else:
                await self.original_interaction.response.send_message(embed=embed, view=self if self.total_pages > 1 else None, ephemeral=ephemeral)
            if self.total_pages <=1: self.stop()
            return

        # For dynamic loading, get first page items
        if self.dynamic_loader:
            page_items = await self.get_page_items(0)
            embed = self.page_formatter(page_items, 1, self.total_pages, self.original_interaction)
        else:
            embed = self.get_current_page_embed()
            
        self._update_button_states()
        if self.original_interaction.response.is_done():
            self.message = await self.original_interaction.followup.send(embed=embed, view=self, ephemeral=ephemeral)
        else:
            # This is the initial response to the command interaction
            await self.original_interaction.response.send_message(embed=embed, view=self, ephemeral=ephemeral)
            self.message = await self.original_interaction.original_response()

    async def _go_to_page(self, page_num: int, interaction: discord.Interaction):
        """Helper to set page, update message, and ensure interaction is handled."""
        self.current_page = max(0, min(page_num, self.total_pages - 1))
        await self.update_message(interaction_for_ack=interaction)


    @ui.button(label="|< First", style=discord.ButtonStyle.secondary, row=0, custom_id="pg_first")
    async def first_page_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._go_to_page(0, interaction)

    @ui.button(label="< Prev", style=discord.ButtonStyle.primary, row=0, custom_id="pg_prev")
    async def prev_page_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._go_to_page(self.current_page - 1, interaction)


    @ui.button(label="Jump", style=discord.ButtonStyle.success, row=0, custom_id="pg_jump")
    async def jump_to_page_button(self, interaction: discord.Interaction, button: ui.Button):
        async def modal_callback(target_page_0_indexed: int):
            # This callback is from the modal. The modal's interaction is separate.
            # We need to update the original message using self.message.
            # The modal interaction itself should be acked by the modal's on_submit.
            self.current_page = target_page_0_indexed
            await self.update_message() # Edit the original message

        modal = JumpToPageModal(max_pages=self.total_pages, current_page_callback=modal_callback)
        await interaction.response.send_modal(modal) # This responds to the button interaction


    @ui.button(label="Next >", style=discord.ButtonStyle.primary, row=0, custom_id="pg_next")
    async def next_page_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._go_to_page(self.current_page + 1, interaction)

    @ui.button(label="Last >|", style=discord.ButtonStyle.secondary, row=0, custom_id="pg_last")
    async def last_page_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._go_to_page(self.total_pages - 1, interaction)

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                if isinstance(item, ui.Button):
                    item.disabled = True
            try:
                timeout_embed = self.get_current_page_embed() 
                current_footer = timeout_embed.footer.text if timeout_embed.footer and timeout_embed.footer.text else None
                
                if current_footer:
                    timeout_embed.set_footer(text=f"{current_footer} (Pagination timed out)")
                else:
                    timeout_embed.set_footer(text="Pagination timed out.")

                await self.message.edit(embed=timeout_embed, view=self) 
            except discord.NotFound: pass 
            except discord.HTTPException as e: logger.warning(f"HTTPException during pagination timeout edit: {e}")
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original command user can interact with the pagination."""
        if interaction.user.id == self.interaction_owner_id:
            return True
        else:
            await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)
            return False

logger.info("Pagination utility module loaded.")