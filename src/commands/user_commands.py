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
