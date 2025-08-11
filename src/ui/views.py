import discord
from typing import TYPE_CHECKING
from src.ui.modals import LeetCodeUsernameModal


if TYPE_CHECKING:
    from src.bot.leetcode_bot import LeetCodeBot


class WelcomeView(discord.ui.View):
    """View for welcome message with registration button"""

    def __init__(self, user: discord.Member, bot: "LeetCodeBot"):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.user = user
        self.bot = bot

    @discord.ui.button(
        label="Register with Leetcode Username",
        style=discord.ButtonStyle.primary,
        emoji="📝",
    )
    async def register_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This registration is not for you!", ephemeral=True
            )
            return

        modal = LeetCodeUsernameModal(self.user, self.bot)
        await interaction.response.send_modal(modal)

    async def on_timeout(self):
        """Disable all buttons when timeout occurs"""
        for item in self.children:
            item.disabled = True
