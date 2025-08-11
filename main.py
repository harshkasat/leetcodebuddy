import discord
from discord.ext import commands
import asyncio
import logging
import os
from dotenv import load_dotenv

from src.config.settings import BotConfig
from src.bot.leetcode_bot import LeetCodeBot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the bot"""
    try:
        # Initialize configuration
        config = BotConfig()

        # Initialize and run the bot
        bot = LeetCodeBot(config)
        bot.run()

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
