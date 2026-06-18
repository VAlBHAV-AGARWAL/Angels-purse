# cogs/help.py (With multi-part detailed descriptions)
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
import logging
import os
from utils.styles import COLORS, EMOJIS

logger = logging.getLogger('cog.help')

VOTE_LINK = os.getenv('VOTE_LINK')
DONATION_INFO = os.getenv('DONATION_INFO')

COMMAND_INFO = {
    "settings": {
        "description": {
            "intro": "The main administrative hub for the bot. It opens an interactive panel to manage all core features.",
            "features": [
                {"name": "⚙️ Assignment Settings", "value": "Choose your server's workflow: track work by Channel, by entire Forum, or by individual Post."},
                {"name": "📜 Task Management", "value": "Create and manage the list of tasks your team performs (e.g., TYPESETTING, CLEANING)."},
                {"name": "📈 Rate Management", "value": "Set payment rates for tasks. Rates can be server-wide (default) or specific to a channel, forum, or post."},
                {"name": "🔒 Restriction Management", "value": "**Crucial for security.** Grant roles permission to use specific bot commands. By default, only the Server Owner has access and must grant permissions to other roles."},
                {"name": "🗄️ Server Data", "value": "Create backups, export all data to a formatted Excel file, or clear server data with granular options."}
            ]
        },
        "usage": "`/settings`",
        "permission": "Requires a role with `/settings` permission. Initially, only the Server Owner can use this.",
        "emoji": EMOJIS['TOOL']
    },
    "ledger": {
        "description": {
            "intro": "Displays a detailed, paginated history of transactions. It has different modes based on the options you provide.",
            "features": [
                {"name": "My Ledger (No Options)", "value": "Running `/ledger` with no options shows your own personal transaction history."},
                {"name": "User's Ledger", "value": "Using `/ledger user:@user` allows you to view the complete transaction history for a specific user."},
                {"name": "Context Ledger", "value": "Using `/ledger context:<channel/post>` shows all transactions that have occurred within that specific context."}
            ]
        },
        "usage": "`/ledger [user:@user] [context:<channel/post>]`",
        "permission": "Viewing your own ledger is available to everyone. Viewing another user's or a context's ledger requires a role with `/ledger` permission.",
        "emoji": "📖"
    },
    "add": {
        "description": "Adds currency to a user's balance for a completed task. This is the primary command for logging work.",
        "usage": "`/add amount:<amount> context:<channel/post> task:<task_name> reason:<reason> [user:@user]`",
        "permission": "Requires a role with `/add` permission granted in `/settings`.",
        "emoji": "➕"
    },
    "less": {
        "description": "Removes currency from a user's balance. Useful for corrections or deductions.",
        "usage": "`/less amount:<amount> context:<channel/post> task:<task_name> reason:<reason> [user:@user]`",
        "permission": "Requires a role with `/less` permission granted in `/settings`.",
        "emoji": "➖"
    },
    "bal": {
        "description": "Checks your own current balance in the server's economy.",
        "usage": "`/bal`",
        "permission": "Available to everyone.",
        "emoji": EMOJIS['WALLET']
    },
    "balance": {
        "description": "Checks the balance of another user in the server.",
        "usage": "`/balance user:@user`",
        "permission": "Requires a role with `/balance` permission granted in `/settings`.",
        "emoji": EMOJIS['MONEY']
    },
    "lb": {
        "description": "Shows the server-wide leaderboard, ranking users by their balance.",
        "usage": "`/lb`",
        "permission": "Requires a role with `/lb` permission granted in `/settings`.",
        "emoji": EMOJIS['TROPHY']
    },
    "rates": {
        "description": "Checks the effective payment rate for a specific task in a given context (channel or post).",
        "usage": "`/rates task_name:<task_name> [context:<channel/post>]`",
        "permission": "Available to everyone.",
        "emoji": EMOJIS['CHART_UP']
    },
    "register": {
        "description": "Allows you to register or update your contact information (email and payment method) for payroll purposes.",
        "usage": "`/register email:<your_email> payment_method:<your_info>`",
        "permission": "Available to everyone.",
        "emoji": EMOJIS['MAIL']
    },
    "emails": {
        "description": "Allows an admin to view a user's registered email address.",
        "usage": "`/emails user:@user`",
        "permission": "Requires a role with `/emails` permission granted in `/settings`.",
        "emoji": "📧"
    },
    "pay": {
        "description": "Allows an admin to view a user's registered payment method details.",
        "usage": "`/pay user:@user`",
        "permission": "Requires a role with `/pay` permission granted in `/settings`.",
        "emoji": EMOJIS['DOLLAR']
    },
    "report": {
        "description": "Sends a private report or feedback message directly to the bot owner.",
        "usage": "`/report message:<your_message>`",
        "permission": "Available to everyone.",
        "emoji": EMOJIS['WARNING']
    },
    "ping": {
        "description": "Checks the bot's current responsiveness and latency to Discord's servers.",
        "usage": "`/ping`",
        "permission": "Available to everyone.",
        "emoji": "🏓"
    },
}

class HelpView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(self.CommandSelect())
        
        if VOTE_LINK:
            self.add_item(ui.Button(label="Vote for Bot", emoji="👍", url=VOTE_LINK, row=1))
        
        if DONATION_INFO:
            support_button = ui.Button(label="Support the Bot", style=discord.ButtonStyle.success, emoji="💖", row=1)
            support_button.callback = self.support_button
            self.add_item(support_button)

    async def support_button(self, interaction: Interaction):
        embed = discord.Embed(
            title="Support Development",
            description=DONATION_INFO,
            color=COLORS["PINK"]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    class CommandSelect(ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=f"/{name}", 
                                     description=(info['description']['intro'] if isinstance(info['description'], dict) else info['description'])[:100], 
                                     emoji=info.get('emoji'))
                for name, info in sorted(COMMAND_INFO.items())
            ]
            super().__init__(placeholder="Select a command for detailed info...", options=options)

        async def callback(self, interaction: Interaction):
            command_name = self.values[0].lstrip('/')
            info = COMMAND_INFO.get(command_name)
            if not info:
                await interaction.response.send_message("Could not find info for that command.", ephemeral=True)
                return

            description_data = info.get('description')
            
            if isinstance(description_data, dict):
                embed = discord.Embed(
                    title=f"{info.get('emoji', '')} Command: `/{command_name}`",
                    description=description_data.get('intro'),
                    color=COLORS["INFO"]
                )
                for feature in description_data.get('features', []):
                    embed.add_field(name=feature['name'], value=feature['value'], inline=False)
            else:
                embed = discord.Embed(
                    title=f"{info.get('emoji', '')} Command: `/{command_name}`",
                    description=description_data,
                    color=COLORS["INFO"]
                )
            
            embed.add_field(name="Usage", value=f"`{info.get('usage')}`", inline=False)
            embed.add_field(name="Permission", value=info.get('permission'), inline=False)
            
            await interaction.response.edit_message(embed=embed)


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Get detailed information about bot commands.")
    async def help_command(self, interaction: Interaction):
        embed = discord.Embed(
            title=f"{EMOJIS['BOOK']} The Angel's Purse Help Desk",
            description="Welcome! Please select a command from the dropdown menu below to see its detailed description, usage, and required permissions.",
            color=COLORS["PRIMARY"]
        )
        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))