# cogs/settings_views/rate_view.py (Fix for InteractionResponded error)
import discord
from discord import ui, Interaction
from typing import List, Optional, Union
import database
from utils.styles import COLORS, EMOJIS
from utils.confirmation import ConfirmationView

# --- Reusable UI Components ---

class SetRateModal(ui.Modal, title="Set/Update Rate"):
    rate_input = ui.TextInput(label="Rate Amount", placeholder="e.g., 1.25", required=True)
    def __init__(self, task_name: str, current_rate: Optional[float]):
        super().__init__()
        self.value = None
        self.rate_input.label = f"New rate for {task_name}"
        if current_rate is not None: self.rate_input.default = str(current_rate)

    async def on_submit(self, interaction: Interaction):
        try:
            rate = float(self.rate_input.value)
            if rate < 0:
                await interaction.response.send_message("Rate must be a positive number.", ephemeral=True)
                return
            self.value = rate
            # Defer the modal's interaction so it closes cleanly
            await interaction.response.defer() 
        except ValueError:
            await interaction.response.send_message("Invalid number format.", ephemeral=True)
        self.stop()

class PostSelect(ui.Select):
    """A select menu that smartly finds both active and archived forum posts."""
    def __init__(self, placeholder: str):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.callback = self.on_select

    async def populate_options(self, interaction: Interaction):
        options = []
        # Active threads first
        for thread in interaction.guild.threads:
            if len(options) >= 25: break
            if isinstance(thread.parent, discord.ForumChannel):
                options.append(discord.SelectOption(label=f"{thread.parent.name}/{thread.name}", value=str(thread.id)))
        # Then archived threads
        for forum in interaction.guild.forums:
            if len(options) >= 25: break
            try:
                async for thread in forum.archived_threads(limit=100):
                    if len(options) >= 25: break
                    if not any(opt.value == str(thread.id) for opt in options):
                        options.append(discord.SelectOption(label=f"{thread.parent.name}/{thread.name} (Archived)", value=str(thread.id)))
            except discord.Forbidden: continue
        self.options = options
    
    async def on_select(self, interaction: Interaction):
        pass

# --- Main UI Views ---

class ManageContextRatesView(ui.View):
    def __init__(self, original_interaction: Interaction, context_type: str, context_object: Optional[Union[discord.TextChannel, discord.ForumChannel, discord.Thread]] = None):
        super().__init__(timeout=300)
        self.original_interaction = original_interaction
        self.context_type = context_type
        self.context_object = context_object
        self.tasks = []
        self.rates = {}
        # We need a reference to the message to edit it later
        self.message: Optional[discord.Message] = None

    async def refresh(self, interaction: Optional[Interaction] = None):
        # Always use the original interaction for guild info
        gid, gname = self.original_interaction.guild_id, self.original_interaction.guild.name
        self.tasks = await database.get_tasks(gid, gname)
        
        if self.context_type == "default": self.rates = await database.get_default_rates(gid, gname)
        elif self.context_type == "channel" and self.context_object: self.rates = await database.get_channel_rates(gid, gname, self.context_object.id)
        elif self.context_type == "forum" and self.context_object: self.rates = await database.get_forum_rates(gid, gname, self.context_object.id)
        elif self.context_type == "post" and self.context_object: self.rates = await database.get_post_rates(gid, gname, self.context_object.id)

        self.update_components()
        embed = self.create_embed()

        # If an interaction is provided (initial load), use it. Otherwise, edit the stored message.
        if interaction and not interaction.response.is_done():
            await interaction.response.edit_message(content=None, embed=embed, view=self)
            self.message = await interaction.original_response()
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    def update_components(self):
        self.clear_items()
        if self.tasks:
            set_select = ui.Select(placeholder="Select a task to SET/UPDATE its rate...", options=[discord.SelectOption(label=t['task_name']) for t in self.tasks[:25]])
            set_select.callback = self.on_set_rate_select
            self.add_item(set_select)
            
            remove_options = [discord.SelectOption(label=t['task_name']) for t in self.tasks if t['task_name'] in self.rates]
            if remove_options:
                remove_select = ui.Select(placeholder="Select a task to REMOVE its rate...", options=remove_options)
                remove_select.callback = self.on_remove_rate_select
                self.add_item(remove_select)
        
        back_button = ui.Button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=4)
        back_button.callback = self.back
        self.add_item(back_button)

    def create_embed(self) -> discord.Embed:
        title = "Rate Management"
        if self.context_type == "default":
            title = "🌍 Manage Default Server Rates"
        elif self.context_type == "channel" and self.context_object:
            title = f"📁 Rates for #{self.context_object.name}"
        elif self.context_type == "forum" and self.context_object:
            title = f"📖 Rates for Forum: {self.context_object.name}"
        elif self.context_type == "post" and self.context_object:
            title = f"📝 Rates for Post: {self.context_object.name}"
            
        embed = discord.Embed(title=title, color=COLORS["INFO"])
        desc = [f"**`{task['task_name']}`**: {'**${:,.2f}**'.format(self.rates.get(task['task_name'])) if self.rates.get(task['task_name']) is not None else '*Not Set*'}" for task in sorted(self.tasks, key=lambda t: t['rank'])]
        embed.description = "\n".join(desc) if desc else "No tasks defined. Please add tasks first."
        return embed

    async def on_set_rate_select(self, interaction: Interaction):
        task_name = interaction.data['values'][0]
        modal = SetRateModal(task_name, self.rates.get(task_name))
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        if modal.value is not None:
            gid, gname = interaction.guild_id, interaction.guild.name
            payload = {task_name: modal.value}
            if self.context_type == "default": await database.update_default_rates(gid, gname, payload)
            elif self.context_type == "channel": await database.update_channel_rates(gid, gname, self.context_object.id, payload)
            elif self.context_type == "forum": await database.update_forum_rates(gid, gname, self.context_object.id, payload)
            elif self.context_type == "post": await database.update_post_rates(gid, gname, self.context_object.id, payload)
            
            # Refresh the view without passing the modal's interaction
            await self.refresh()

    async def on_remove_rate_select(self, interaction: Interaction):
        # This part still needs full implementation with confirmation
        task_name = interaction.data['values'][0]
        # ... (Confirmation logic and actual deletion)
        await self.refresh()

    async def back(self, interaction: Interaction):
        embed = discord.Embed(title="📈 Rate Management", description="Select a rate category to manage.", color=COLORS["INFO"])
        from .rate_view import RateManagementView
        view = RateManagementView(self.original_interaction)
        await view.update_buttons(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class ForumOrPostSelectView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction

    @ui.button(label="Manage by Forum", style=discord.ButtonStyle.primary, emoji="📖")
    async def select_forum(self, interaction: Interaction, button: ui.Button):
        view = ui.View(timeout=180)
        forum_select = ui.ChannelSelect(placeholder="Select a Forum to manage its rates...", channel_types=[discord.ChannelType.forum])
        async def callback(inner_interaction: Interaction):
            forum_id = int(inner_interaction.data['values'][0])
            forum = inner_interaction.guild.get_channel(forum_id)
            manage_view = ManageContextRatesView(self.original_interaction, "forum", forum)
            await manage_view.refresh(inner_interaction)
        forum_select.callback = callback
        view.add_item(forum_select)
        await interaction.response.edit_message(content="Please select a forum:", view=view)

    @ui.button(label="Manage by Post", style=discord.ButtonStyle.primary, emoji="📝")
    async def select_post(self, interaction: Interaction, button: ui.Button):
        all_posts_list = []
        for thread in interaction.guild.threads:
            if isinstance(thread.parent, discord.ForumChannel):
                all_posts_list.append(thread)
        for forum in interaction.guild.forums:
            try:
                async for thread in forum.archived_threads(limit=None):
                    all_posts_list.append(thread)
            except discord.Forbidden:
                continue
        
        if not all_posts_list:
            await interaction.response.edit_message(content="No accessible posts found in any forum.", view=None)
            return

        all_posts_list.sort(key=lambda x: x.created_at, reverse=True)
        options = [discord.SelectOption(label=f"#{post.name[:90]}", value=str(post.id), description=f"in {post.parent.name[:90]}") for post in all_posts_list[:25]]
        post_select = ui.Select(placeholder="Select a post to manage its rates...", options=options)

        async def callback(inner_interaction: Interaction):
            post_id = int(inner_interaction.data['values'][0])
            thread = inner_interaction.guild.get_thread(post_id) or next((p for p in all_posts_list if p.id == post_id), None)
            if thread:
                manage_view = ManageContextRatesView(self.original_interaction, "post", thread)
                await manage_view.refresh(inner_interaction)
            else:
                await inner_interaction.response.send_message("Could not find the selected post.", ephemeral=True)
        post_select.callback = callback
        
        view = ui.View(timeout=180)
        view.add_item(post_select)
        back_button = ui.Button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=2)
        async def back_callback(back_interaction: Interaction):
            from .rate_view import RateManagementView
            view = RateManagementView(self.original_interaction)
            await view.update_buttons(back_interaction)
            embed = discord.Embed(title="📈 Rate Management", description="Select a rate category to manage.", color=COLORS["INFO"])
            await back_interaction.response.edit_message(content=None, embed=embed, view=view)
        back_button.callback = back_callback
        view.add_item(back_button)
        await interaction.response.edit_message(content="Please select a post:", view=view)

    @ui.button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=1)
    async def back(self, interaction: Interaction, button: ui.Button):
        embed = discord.Embed(title="📈 Rate Management", description="Select a rate category to manage.", color=COLORS["INFO"])
        from .rate_view import RateManagementView
        view = RateManagementView(self.original_interaction)
        await view.update_buttons(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class RateManagementView(ui.View):
    def __init__(self, original_interaction: Interaction):
        super().__init__(timeout=300)
        self.original_interaction = original_interaction
        
    async def update_buttons(self, interaction: Interaction):
        enabled_formats = await database.get_enabled_formats(interaction.guild_id, interaction.guild.name)
        channel_button = discord.utils.get(self.children, custom_id="rate_channel")
        forum_post_button = discord.utils.get(self.children, custom_id="rate_forum_post")
        if channel_button: channel_button.disabled = 'channel_based' not in enabled_formats
        if forum_post_button: forum_post_button.disabled = not ('forum_based' in enabled_formats or 'post_based' in enabled_formats)

    @ui.button(label="Default Rates", style=discord.ButtonStyle.primary, emoji="🌍", custom_id="rate_default")
    async def default_rates(self, interaction: Interaction, button: ui.Button):
        view = ManageContextRatesView(self.original_interaction, "default")
        await view.refresh(interaction)

    @ui.button(label="Channel Rates", style=discord.ButtonStyle.secondary, emoji="📁", custom_id="rate_channel")
    async def channel_rates(self, interaction: Interaction, button: ui.Button):
        view = ui.View(timeout=180)
        channel_select = ui.ChannelSelect(placeholder="Select a text channel to manage its rates...", channel_types=[discord.ChannelType.text])
        async def callback(inner_interaction: Interaction):
            channel_id = int(inner_interaction.data['values'][0])
            channel = inner_interaction.guild.get_channel(channel_id)
            manage_view = ManageContextRatesView(self.original_interaction, "channel", channel)
            await manage_view.refresh(inner_interaction)
        channel_select.callback = callback
        view.add_item(channel_select)
        await interaction.response.edit_message(content="Please select a channel:", view=view)

    @ui.button(label="Forum/Post Rates", style=discord.ButtonStyle.secondary, emoji="📖", custom_id="rate_forum_post")
    async def forum_post_rates(self, interaction: Interaction, button: ui.Button):
        view = ForumOrPostSelectView(self.original_interaction)
        await interaction.response.edit_message(content="Do you want to manage rates for an entire Forum or a specific Post?", embed=None, view=view)

    @ui.button(label="⬅️ Back", style=discord.ButtonStyle.grey, row=2, custom_id="back_to_main")
    async def back_to_main_menu(self, interaction: Interaction, button: ui.Button):
        from ..settings import SettingsMainView
        embed = discord.Embed(title=f"{EMOJIS['TOOL']} Bot Settings Panel", description="Select a category to configure.", color=COLORS["PRIMARY"])
        view = SettingsMainView(self.original_interaction)
        await interaction.response.edit_message(embed=embed, view=view)