# The Angel's Purse Bot

**Mahiru Edition**

A Discord economy bot with flexible payment tracking, role-based access control, and a single management interface.

## What this bot does

- Tracks user balances and transactions.
- Supports three work context types: channel, forum, and forum post.
- Lets server staff configure task rates, permissions, and data management from one `/settings` panel.
- Stores information in a local SQLite database and supports export and backup operations.

## Key Features

- Central `/settings` command for all admin configuration.
- Three assignment modes:
  - Channel-based work logging.
  - Forum-based work logging.
  - Post-based work logging.
- Granular permissions for roles, with no admin commands enabled by default.
- Data export to Excel and database backup support.
- Balance checks, leaderboard, transaction history, and registration for contact info.

## Commands

### User commands
- `/bal` — Check your balance.
- `/ledger` — View your own transaction history.
- `/rates` — Check the rate for a task in a chosen context.
- `/register` — Register or update your contact/payment details.
- `/report` — Send a report to the bot owner.
- `/ping` — Check bot responsiveness.
- `/help` — Get command information.

### Admin commands
- `/settings` — Open the settings panel. All admin controls are available there.
- `/add` — Give currency to a user for completed work.
- `/less` — Remove currency from a user.
- `/balance <user>` — Check another user’s balance.
- `/lb` — View the server economy leaderboard.
- `/ledger <user/context>` — View another user’s or a context’s transaction history.

### Settings panel includes
- Assignment format toggles (channel, forum, post).
- Task management.
- Rate management for default, channel, forum, and post contexts.
- Role-based restrictions and permissions.
- Data management, backups, and exports.

## Project structure
```
- `cogs/`
  - `settings.py` — Main `/settings` command and menu logic.
  - `settings_views/`
    - `assignment_view.py`
    - `data_view.py`
    - `rate_view.py`
    - `restriction_view.py`
    - `task_view.py`
  - `add.py` — Handles `/add`.
  - `bal.py` — Handles `/bal`.
  - `less.py` — Handles `/less`.
  - `lb.py` — Leaderboard command.
  - Other user-facing cogs.
- `db_logic/`
  - `database.py` — Facade for database operations.
  - `_core.py` — Database initialization, pooling, and helpers.
  - `economy_queries.py` — Economy and transaction queries.
  - `rate_queries.py` — Rate management queries.
  - Other query modules.
- `utils/`
  - `checks.py`
  - `confirmation.py`
  - `excel_utils.py`
  - `pagination.py`
  - `styles.py`
- `main.py` — Bot startup and cog loading.
- `requirements.txt` — Python dependencies.
- `Readme.md` — Project documentation.
```
## Installation

1. Clone the repository.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your bot token and settings.
4. Do not commit `.env`.
5. Start the bot:
   `python main.py`

## Configuration

When the bot joins a server, it creates the required database tables automatically. Use `/settings` to configure tasks, rates, permissions, and data options.

## Contributing

To extend the bot:
1. Add UI views inside `cogs/settings_views/`.
2. Add database support in `db_logic/`.
3. Wire the new feature into `cogs/settings.py`.

## License

MIT License.