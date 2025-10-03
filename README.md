
# Multipurpose Discord Bot

A powerful and versatile Discord bot built with `discord.py` that includes a full suite of moderation, fun, and utility commands. This bot is designed to be easily extensible and features secure practices for public use.

## Features

**Security & Permissions**
*   **`.env` for Tokens**: Securely loads the bot token and owner ID from an environment file, preventing sensitive data from being exposed in the code.
*   **Permission-based Commands**: Restricts moderation commands using Discord's built-in permission system (`@commands.has_permissions`).
*   **Role Hierarchy Checks**: Automatically prevents moderators from affecting users with higher or equal roles.
*   **Owner-Only Commands**: Special commands are restricted to the bot owner's ID.
*   **Robust Error Handling**: Catches common errors, such as missing permissions or arguments, and sends helpful feedback to the user.

**Moderation**
*   `!kick [member] [reason]`: Kicks a specified member from the server.
*   `!ban [member] [reason]`: Permanently bans a member from the server.
*   `!unban [member#tag]`: Unbans a member using their full Discord tag.
*   `!role [member] [role]`: Adds or removes a specified role from a member.

**Fun & Interactive**
*   `!afk [reason]`: Sets your status as AFK. The bot will notify others if they mention you. Your AFK status is automatically removed when you send a message.
*   `!fakenitro [user]`: Pranks a user with an interactive, fake Nitro gift embed.

**Premium System (Owner Only)**
*   `!premium activate [server_id]`: Activates the bot's premium features for a specific server.
*   `!premium deactivate [server_id]`: Deactivates the premium features for a server.
*   `!ticketsetup [category] [log_channel]`: (Premium Feature) Sets up a ticket panel with an "Open Ticket" button.

**Owner Utilities (No Prefix)**
*   `sync`: Synchronizes all slash commands with Discord globally. This command only works when sent by the bot owner and does not require the bot's command prefix.

## Getting Started

### Prerequisites
*   Python 3.8 or higher.
*   Access to the [Discord Developer Portal](https://discord.com/developers/applications).
*   **Privileged Gateway Intents**: On the bot's page in the Discord Developer Portal, enable `Message Content Intent` and `Server Members Intent`.

### Installation
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/joker09245/Multipurpose.discord-bot.git
    cd your-repo-name
    ```
2.  **Install dependencies**:
    ```bash
    pip install -U -r requirements.txt
    ``
    *(Note: You will need to create a `requirements.txt` file by running `pip freeze > requirements.txt` after installing the libraries `discord.py` and `python-dotenv`.)*
3.  **Set up environment variables**:
    *   Create a file named `.env` in the root of your project.
    *   Add your bot token and owner ID to the file.
        ```ini
        DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
        OWNER_ID=YOUR_DISCORD_USER_ID
        ```
    *   Find your owner ID by enabling Developer Mode in Discord (`Settings > Advanced`) and right-clicking your profile to "Copy User ID."
4.  **Create premium data file**:
    *   Create an empty JSON file named `premium_servers.json` in the project root.
        ```json
        {}
        ```

### Running the Bot
To start the bot, run the following command from your terminal:
```bash
python main.py
