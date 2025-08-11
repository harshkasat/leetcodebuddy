import os
from dataclasses import dataclass
import discord


@dataclass
class BotConfig:
    """Bot configuration settings"""

    def __post_init__(self):
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.main_guild_id = int(os.getenv("MAIN_GUILD_ID"))

        # Bot settings
        self.command_prefix = "!"
        self.max_group_size = 5
        self.daily_points = 5
        self.leaderboard_limit = 10

        # Discord intents
        self.intents = discord.Intents.default()
        self.intents.message_content = True
        self.intents.guilds = True
        self.intents.members = True

        # Validate required environment variables
        self._validate_config()

    def _validate_config(self):
        """Validate that all required config is present"""
        required_vars = [
            self.discord_token,
            self.supabase_url,
            self.supabase_key,
            self.main_guild_id,
        ]

        if not all(required_vars):
            raise ValueError("Missing required environment variables")
