import discord
from discord.ext import commands
import logging
from typing import Optional


from src.config.settings import BotConfig
from src.database.database_manager import DatabaseManager
from src.services.leetcode_services import LeetCodeService
from src.services.group_services import GroupService
from src.tasks.scheduled_tasks import ScheduledTasks
from src.commands.user_commands import UserCommands
from src.events.event_handlers import EventHandlers


logger = logging.getLogger(__name__)


class LeetCodeBot(commands.Bot):
    """Main bot class that orchestrates all components"""

    def __init__(self, config: BotConfig):
        # Initialize Discord bot
        super().__init__(command_prefix=config.command_prefix, intents=config.intents)
        self.config = config
        self.db = DatabaseManager(config.supabase_url, config.supabase_key)
        self.leetcode_service = LeetCodeService()
        self.group_service = GroupService(self.db, config.max_group_size)
        self.scheduled_tasks = ScheduledTasks(self)

    async def setup_hook(self):
        """Setup all command cogs and event handlers"""
        try:
            await self.add_cog(UserCommands(self))
            await self.add_cog(EventHandlers(self))
            logger.info("All cogs loaded successfully")
        except Exception as e:
            logger.error(f"Error setting up cogs: {e}")
            raise

    async def close(self):
        """Cleanup when bot is shutting down"""
        try:
            # Stop scheduled tasks
            self.scheduled_tasks.stop_all_tasks()
            await self.leetcode_service.close_session()
            await super().close()
            logger.info("Bot shutdown complete")

        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")

    def run(self):
        """Run the bot"""
        try:
            super().run(self.config.discord_token)
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise
