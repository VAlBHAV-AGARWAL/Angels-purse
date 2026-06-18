# The Angel's Purse Bot

**Mahiru Edition**

A professional-grade, multi-faceted economy bot for Discord. It has evolved from a simple currency system into a highly configurable administrative tool designed for communities with complex workflows, such as scanlation groups or creative teams.

Its core strength lies in its flexibility. Server administrators can use a single, powerful `/settings` command to tailor the bot's behavior to their specific needs, choosing between channel-based, forum-based, or post-based tracking for work and payments. This is complemented by a robust, additive permission system that allows delegation of specific bot commands to non-administrator roles, ensuring both security and operational efficiency.

## Features

- **Centralized Admin Panel:** A single `/settings` command provides an interactive UI for managing all bot features, eliminating the need for dozens of separate slash commands.
- **Flexible Work Contexts:** Supports three distinct workflows for logging work, configurable via the settings panel:
  - **Channel Based:** Traditional work logged against a specific text channel.
  - **Forum Based:** Work logged against an entire forum, perfect for tracking large projects (e.g., a comic series).
  - **Post Based:** Work logged against a specific forum post, ideal for tracking individual tasks (e.g., a chapter).
- **True Role-Based Access Control (RBAC):** A granular, additive permission system. By default, users have no access to admin commands. Permissions must be explicitly granted to roles via the `/settings` panel.
- **Complete Data Management:** Admins can create full database backups, export all server data to a formatted Excel file, and securely clear data through the settings panel.
- **Robust Core Features:** Includes user balance tracking, detailed transaction history (`/ledger`), a server leaderboard, user registration for contact info, and automatic daily backups.
- **Professional Architecture:** Built with a clean, scalable structure using facades for both database logic and UI components, ensuring the bot is easy to maintain and expand.

## Project Structure
.
├── cogs/
│ ├── settings.py # Facade for the /settings command and main menu UI
│ ├── settings_views/ # Directory for individual settings panel UIs
│ │ ├── init.py
│ │ ├── assignment_view.py # Toggle assignment format settings
│ │ ├── data_view.py # Backup, export, and data management
│ │ ├── rate_view.py # Rate management for all contexts
│ │ ├── restriction_view.py # Role restrictions and permissions
│ │ └── task_view.py # Task CRUD operations
│ ├── add.py # Handles the smart /add command
│ ├── bal.py # Handles the /bal command
│ └── (other user-facing cogs...)
├── db_logic/
│ ├── init.py
│ ├── _core.py # Core DB logic (pooling, cache, table creation)
│ ├── economy_queries.py # Economy and transaction queries
│ ├── rate_queries.py # Rate management queries
│ └── (other query modules...)
├── utils/
│ ├── checks.py # Permission and restriction checks
│ ├── confirmation.py # Reusable confirmation dialogs
│ ├── excel_utils.py # Excel export functionality
│ ├── pagination.py # Modern pagination system
│ └── styles.py # Consistent UI styling
├── .env # Environment variables
├── database.py # Facade for all database operations
├── main.py # Main bot file (startup, cog loading)
├── requirements.txt # Python dependencies
└── README.md # This file
code
Code
## Commands Overview

The bot has been refactored to centralize all administrative functions into a single, powerful command.

### Primary User Commands
- `/bal`: Check your own balance.
- `/ledger`: View your personal transaction history.
- `/rates`: Check the payment rate for a task in a specific context.
- `/register`: Register or update your contact/payment details.
- `/report`: Report an issue to the bot owner.
- `/ping`: Check the bot's responsiveness.
- `/help`: Get information about available commands.

### Management & Admin Commands
- `/settings`: **(Primary Hub)** Opens the main interactive settings panel. All other admin functions are accessed through this panel's UI buttons.
- `/add`: Adds currency to a user for work done.
- `/less`: Removes currency from a user.
- `/balance <user>`: Check another user's balance.
- `/lb`: View the server economy leaderboard.
- `/ledger <user/context>`: (Admin) View another user's or a context's transaction history.

The `/settings` panel includes management for:
- **Assignment Settings:** Toggle which work contexts (Channel, Forum, Post) are enabled.
- **Task Management:** Add, remove, and list all tasks.
- **Rate Management:** Set default, channel, forum, and post-specific rates.
- **Restriction Management:** Grant specific command permissions to roles.
- **Server Data:** Create backups, export to Excel, and clear data.

## Installation

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your own values.
4. Make sure `.env` is not committed to git.
5. Run the bot: `python main.py`

## Configuration

The bot automatically creates necessary database tables and configurations when it joins a server. The server owner can then use the `/settings` command to configure all aspects of the bot.

## Architecture Highlights

- **Facade Pattern:** Clean separation between UI, business logic, and data access.
- **Modern Discord.py UI:** Uses `discord.ui` for an intuitive and interactive experience.
- **Async Database Operations:** Efficient connection pooling and async database operations for `sqlite3`.
- **Modular Design:** Easy to extend with new features and maintain existing code.
- **Professional Error Handling:** Comprehensive logging and user-friendly error messages.

## Contributing

This bot is designed with extensibility in mind. New features can be added by:
1. Creating new UI views in `cogs/settings_views/`.
2. Adding corresponding database logic in `db_logic/`.
3. Integrating with the main settings facade in `cogs/settings.py`.

## License

This project is licensed under the MIT License.