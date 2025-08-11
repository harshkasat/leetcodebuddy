import discord
from discord.ext import commands
import logging
from typing import TYPE_CHECKING
from src.ui.views import WelcomeView

if TYPE_CHECKING:
    from bot.leetcode_bot import LeetCodeBot

logger = logging.getLogger(__name__)


class EventHandlers(commands.Cog):
    """Handles Discord events"""

    def __init__(self, bot: "LeetCodeBot"):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Bot ready event"""
        logger.info(f"{self.bot.user} has landed!")
        await self.bot.leetcode_service.init_session()
        self.bot.scheduled_tasks.start_all_tasks()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joining the server"""
        try:
            # Check if user is already registered
            user_id = str(member.id)
            existing_user = self.bot.db.get_user(user_id)

            if existing_user:
                # User is already registered
                embed = discord.Embed(
                    title="Welcome back! 🎉",
                    description=f"Hey {member.mention}, you're already registered!",
                    color=0x00FF00,
                )
                embed.add_field(
                    name="Your Leetcode Username",
                    value=existing_user["leetcode_username"],
                    inline=False,
                )
                embed.add_field(
                    name="Quick Commands",
                    value="`!profile` - View your stats\n`!leaderboard` - See rankings",
                    inline=False,
                )

                await self._send_welcome_message(member, embed)
                return

            # New user - send welcome message with registration form
            embed = discord.Embed(
                title="🎉 Welcome to Leetcode Buddy!",
                description=f"Hey {member.mention}! Ready to level up your coding skills?",
                color=0x7289DA,
            )
            embed.add_field(
                name="What is Leetcode Buddy?",
                value="• Daily Leetcode challenges sent to small groups (max 5 people)\n• Solve questions within 24 hours to earn points\n• Compete on monthly global and weekly group leaderboards\n• Build consistency and accountability!",
                inline=False,
            )
            embed.add_field(
                name="Getting Started",
                value="Click the button below to register with your Leetcode username.",
                inline=False,
            )
            embed.set_footer(text="Registration expires in 5 minutes")

            view = WelcomeView(member, self.bot)
            await self._send_welcome_message(member, embed, view)

        except Exception as e:
            logger.error(f"Error handling member join: {e}")

    async def _send_welcome_message(
        self, member: discord.Member, embed: discord.Embed, view: discord.ui.View = None
    ):
        """Send welcome message via DM or general channel"""
        try:
            if view:
                await member.send(embed=embed, view=view)
            else:
                await member.send(embed=embed)
        except discord.Forbidden:
            # If DM fails, send in general channel
            general_channel = discord.utils.get(member.guild.channels, name="general")
            if general_channel:
                if view:
                    await general_channel.send(
                        f"{member.mention}", embed=embed, view=view
                    )
                else:
                    await general_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Handle command errors"""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing required argument. Use `!help` for command usage.")
        else:
            logger.error(f"Command error: {error}")
            await ctx.send("An error occurred while processing the command.")
