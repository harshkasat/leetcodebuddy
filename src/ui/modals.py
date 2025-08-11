import discord
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from src.bot.leetcode_bot import LeetCodeBot

logger = logging.getLogger(__name__)


class LeetCodeUsernameModal(discord.ui.Modal, title="Welcome to Leetcode Buddy! 🧠"):
    """Modal for collecting LeetCode username during registration"""

    def __init__(self, user: discord.Member, bot: "LeetCodeBot"):
        super().__init__()
        self.user = user
        self.bot = bot

    leetcode_username = discord.ui.TextInput(
        label="Your Leetcode Username",
        placeholder="Enter your Leetcode username here...",
        required=True,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            user_id = str(self.user.id)
            username = self.leetcode_username.value.strip()

            # Validate LeetCode username
            is_valid = await self.bot.leetcode_service.validate_username(username)
            if not is_valid:
                await interaction.followup.send(
                    f"❌ The Leetcode username '{username}' doesn't exist or is invalid. Please try again with `!update_username <correct_username>`",
                    ephemeral=True,
                )
                return

            # Check if user already exists
            existing_user = self.bot.db.get_user(user_id)
            if existing_user:
                await interaction.followup.send(
                    "You're already registered! Welcome back! 🎉", ephemeral=True
                )
                return

            # Create new user
            user_data = self.bot.db.create_user(user_id, username)
            if not user_data:
                await interaction.followup.send(
                    "❌ Registration failed. Please try again or contact an admin.",
                    ephemeral=True,
                )
                return

            # Get guild
            guild = self.bot.get_guild(self.bot.config.main_guild_id)
            if not guild:
                await interaction.followup.send(
                    "❌ Server not found. Please contact admin.", ephemeral=True
                )
                return

            # Assign user to a group
            group_info = await self.bot.group_service.assign_user_to_group(
                self.user, guild
            )
            if not group_info:
                await interaction.followup.send(
                    "❌ Failed to assign to group. Please try again.", ephemeral=True
                )
                return

            # Send success message
            embed = discord.Embed(
                title="🎉 Registration Successful!",
                description=f"Welcome to Leetcode Buddy, {self.user.mention}!",
                color=0x00FF00,
            )
            embed.add_field(name="Leetcode Username", value=username, inline=True)
            embed.add_field(
                name="Assigned Group", value=group_info["name"], inline=True
            )
            embed.add_field(
                name="Group Channel",
                value=f"<#{group_info['channel_id']}>",
                inline=True,
            )
            embed.add_field(
                name="What's Next?",
                value="• Daily questions will be posted at 12 AM UTC\n• Solve them within 24 hours to earn points\n• Check leaderboards with `!leaderboard`",
                inline=False,
            )
            embed.set_footer(text="Good luck with your coding journey! 💪")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in registration modal: {e}")
            try:
                await interaction.followup.send(
                    "❌ An error occurred during registration. Please try again.",
                    ephemeral=True,
                )
            except discord.errors.NotFound:
                await interaction.response.send_message(
                    "❌ An error occurred during registration. Please try again.",
                    ephemeral=True,
                )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.error(f"Modal error: {error}")
        try:
            await interaction.followup.send(
                "❌ Something went wrong. Please try again.", ephemeral=True
            )
        except (discord.errors.InteractionResponded, discord.errors.NotFound):
            await interaction.response.send_message(
                "❌ Something went wrong. Please try again.", ephemeal=True
            )
