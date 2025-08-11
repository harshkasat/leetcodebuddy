import discord
from typing import Optional, Dict, Any
import logging
from src.database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class GroupService:
    """Handles group management operations"""

    def __init__(self, db: DatabaseManager, max_group_size: int = 5):
        self.db = db
        self.max_group_size = max_group_size

    async def assign_user_to_group(
        self, user: discord.Member, guild: discord.Guild
    ) -> Optional[Dict[str, Any]]:
        """Assign user to a group (max 5 per group)"""
        try:
            if not guild:
                logger.error("Guild is None in assign_user_to_group")
                return None

            # Find available group or create new one
            groups = self.db.get_all_groups()
            available_group = None

            for group in groups:
                member_count = len(self.db.get_group_members(group["id"]))
                if member_count < self.max_group_size:
                    available_group = group
                    break

            if not available_group:
                # Create new group
                group_name = f"Group-{len(groups) + 1}"
                available_group = self.db.create_group(group_name)

                if not available_group:
                    logger.error("Failed to create new group")
                    return None

                # Create Discord channel for the group
                channel = await self._create_group_channel(
                    guild, available_group["name"]
                )
                if channel:
                    self.db.update_group_channel(available_group["id"], str(channel.id))
                    available_group["channel_id"] = str(channel.id)

            # Add user to group
            success = self.db.add_member_to_group(available_group["id"], str(user.id))
            if not success:
                logger.error("Failed to add user to group")
                return None

            # Add user to Discord channel
            if available_group.get("channel_id"):
                await self._add_user_to_channel(
                    guild, user, int(available_group["channel_id"])
                )

            return {
                "id": available_group["id"],
                "name": available_group["name"],
                "channel_id": available_group["channel_id"],
            }

        except Exception as e:
            logger.error(f"Error assigning user to group: {e}")
            return None

    async def _create_group_channel(
        self, guild: discord.Guild, group_name: str
    ) -> Optional[discord.TextChannel]:
        """Create a Discord channel for the group"""
        try:
            category = discord.utils.get(guild.categories, name="Leetcode Groups")
            if not category:
                category = await guild.create_category("Leetcode Groups")

            channel = await guild.create_text_channel(
                group_name.lower().replace(" ", "-"),
                category=category,
                topic=f"Leetcode practice group - {group_name}",
            )

            return channel
        except Exception as e:
            logger.error(f"Error creating group channel: {e}")
            return None

    async def _add_user_to_channel(
        self, guild: discord.Guild, user: discord.Member, channel_id: int
    ):
        """Add user to a group channel with permissions"""
        try:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.set_permissions(
                    user,
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                )

                welcome_embed = discord.Embed(
                    title="🎉 New Member Alert!",
                    description=f"Welcome {user.mention} to the group!",
                    color=0x00FF00,
                )
                welcome_embed.add_field(
                    name="Group Info",
                    value="You're now part of a team! Daily challenges will be posted here at 12 AM UTC.",
                    inline=False,
                )
                welcome_embed.add_field(
                    name="Good luck!",
                    value="Let's code together and build those problem-solving skills! 💪",
                    inline=False,
                )

                await channel.send(embed=welcome_embed)
        except Exception as e:
            logger.error(f"Error adding user to channel: {e}")
