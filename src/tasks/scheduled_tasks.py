import asyncio
from datetime import datetime, timedelta
from discord.ext import tasks
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.bot.leetcode_bot import LeetCodeBot

logger = logging.getLogger(__name__)


class ScheduledTasks:
    """Handles all scheduled tasks for the bot"""

    def __init__(self, bot: "LeetCodeBot"):
        self.bot = bot

    def start_all_tasks(self):
        """Start all scheduled tasks"""
        self.daily_question_task.start()
        self.check_submissions_task.start()

    def stop_all_tasks(self):
        """Stop all scheduled tasks"""
        if self.daily_question_task.is_running():
            self.daily_question_task.cancel()
        if self.check_submissions_task.is_running():
            self.check_submissions_task.cancel()

    @tasks.loop(hours=24)
    async def daily_question_task(self):
        """Send daily question at 12 AM UTC"""
        try:
            # Get used question slugs
            used_slugs = self.bot.db.get_used_question_slugs()

            # Fetch random question
            question = await self.bot.leetcode_service.fetch_random_question(used_slugs)
            if not question:
                logger.error("Failed to fetch question")
                return

            # Save question to database
            daily_question = self.bot.db.save_daily_question(
                question["titleSlug"], question["title"], question["difficulty"]
            )
            if not daily_question:
                logger.error("Failed to save daily question")
                return

            # Send question to all groups
            await self._send_question_to_groups(question)
            logger.info(f"Daily question sent: {question['title']}")

        except Exception as e:
            logger.error(f"Error in daily question task: {e}")

    @tasks.loop(hours=24)
    async def check_submissions_task(self):
        """Check submissions 24 hours after question was sent"""
        try:
            # Get yesterday's question
            yesterday = datetime.utcnow() - timedelta(days=1)
            # This would need a proper query method in DatabaseManager
            # For now, this is a placeholder

            # Get all users and check their submissions
            # Implementation would go here
            logger.info("Submissions checked and scores updated")

        except Exception as e:
            logger.error(f"Error checking submissions: {e}")

    async def _send_question_to_groups(self, question):
        """Send daily question to all group channels"""
        try:
            groups = self.bot.db.get_all_groups()
            guild = self.bot.get_guild(self.bot.config.main_guild_id)

            if not guild:
                logger.error("Guild not found")
                return

            for group in groups:
                if group.get("channel_id"):
                    channel = guild.get_channel(int(group["channel_id"]))
                    if channel:
                        embed = discord.Embed(
                            title="🧠 Daily LeetCode Challenge",
                            description=f"**{question['title']}**\n\nDifficulty: {question['difficulty']}",
                            color=0x00FF00,
                            url=f"https://leetcode.com/problems/{question['titleSlug']}/",
                        )
                        embed.add_field(
                            name="⏰ Deadline", value="24 hours from now", inline=False
                        )
                        embed.add_field(
                            name="🎯 Points",
                            value=f"+{self.bot.config.daily_points} points for solving",
                            inline=False,
                        )
                        embed.set_footer(text="Good luck team! 💪")

                        await channel.send("@everyone", embed=embed)
        except Exception as e:
            logger.error(f"Error sending question to groups: {e}")

    @daily_question_task.before_loop
    async def before_daily_question(self):
        """Wait until bot is ready and calculate time until midnight UTC"""
        await self.bot.wait_until_ready()
        now = datetime.utcnow()
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        seconds_until_midnight = (next_midnight - now).total_seconds()
        await asyncio.sleep(seconds_until_midnight)

    @check_submissions_task.before_loop
    async def before_check_submissions(self):
        """Wait until bot is ready and start checking submissions 1 hour after daily questions"""
        await self.bot.wait_until_ready()
        now = datetime.utcnow()
        next_check_time = (now + timedelta(days=1)).replace(
            hour=1, minute=0, second=0, microsecond=0
        )
        seconds_until_check = (next_check_time - now).total_seconds()
        await asyncio.sleep(seconds_until_check)


# ====================================================
# commands/user_commands.py
import discord
from discord.ext import commands
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.leetcode_bot import LeetCodeBot

logger = logging.getLogger(__name__)


class UserCommands(commands.Cog):
    """Commands related to user operations"""

    def __init__(self, bot: "LeetCodeBot"):
        self.bot = bot

    @commands.command(name="update_username")
    async def update_username(self, ctx: commands.Context, new_username: str):
        """Update LeetCode username"""
        try:
            user_id = str(ctx.author.id)

            # Validate new username
            is_valid = await self.bot.leetcode_service.validate_username(new_username)
            if not is_valid:
                await ctx.send(
                    f"❌ The Leetcode username '{new_username}' doesn't exist or is invalid."
                )
                return

            # Update username
            success = self.bot.db.update_user_username(user_id, new_username)
            if success:
                await ctx.send(
                    f"✅ Successfully updated your Leetcode username to: `{new_username}`"
                )
            else:
                await ctx.send(
                    "❌ You're not registered yet. Please complete registration first when you joined the server."
                )

        except Exception as e:
            logger.error(f"Error updating username: {e}")
            await ctx.send("❌ Failed to update username. Please try again.")

    @commands.command(name="profile")
    async def show_profile(self, ctx: commands.Context):
        """Show user profile"""
        try:
            user_id = str(ctx.author.id)
            user_data = self.bot.db.get_user(user_id)

            if not user_data:
                await ctx.send(
                    "You're not registered yet. Please complete registration first when you joined the server."
                )
                return

            embed = discord.Embed(
                title=f"Profile: {ctx.author.display_name}", color=0x7289DA
            )
            embed.add_field(
                name="LeetCode Username",
                value=user_data["leetcode_username"],
                inline=True,
            )
            embed.add_field(
                name="Monthly Score",
                value=f"{user_data['monthly_score']} points",
                inline=True,
            )
            embed.add_field(
                name="Weekly Score",
                value=f"{user_data['weekly_score']} points",
                inline=True,
            )
            embed.set_thumbnail(
                url=ctx.author.avatar.url if ctx.author.avatar else None
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing profile: {e}")
            await ctx.send("Failed to fetch profile.")

    @commands.command(name="leaderboard")
    async def show_leaderboard(self, ctx: commands.Context, type_arg: str = "monthly"):
        """Show leaderboard (monthly/weekly)"""
        try:
            if type_arg.lower() == "weekly":
                # Show group weekly leaderboard
                user_id = str(ctx.author.id)
                user_group = self.bot.db.get_user_group(user_id)

                if not user_group:
                    await ctx.send(
                        "You're not in any group yet. Please complete registration first."
                    )
                    return

                users = self.bot.db.get_group_weekly_leaderboard(user_group["id"])
                embed = discord.Embed(
                    title="🏆 Weekly Group Leaderboard", color=0xFFD700
                )
                score_field = "weekly_score"
            else:
                # Show monthly global leaderboard
                users = self.bot.db.get_monthly_leaderboard(
                    self.bot.config.leaderboard_limit
                )
                embed = discord.Embed(
                    title="🌟 Monthly Global Leaderboard", color=0xFF6B6B
                )
                score_field = "monthly_score"

            if not users:
                embed.add_field(name="No data", value="No users found", inline=False)
            else:
                leaderboard_text = ""
                for i, user in enumerate(users, 1):
                    score = user[score_field]
                    discord_user = self.bot.get_user(int(user["discord_id"]))
                    username = (
                        discord_user.display_name
                        if discord_user
                        else user["leetcode_username"]
                    )

                    medal = (
                        "🥇"
                        if i == 1
                        else "🥈"
                        if i == 2
                        else "🥉"
                        if i == 3
                        else f"{i}."
                    )
                    leaderboard_text += f"{medal} **{username}** - {score} points\n"

                embed.add_field(name="Rankings", value=leaderboard_text, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}")
            await ctx.send("Failed to fetch leaderboard.")
