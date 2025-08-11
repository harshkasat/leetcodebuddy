from supabase import create_client, Client
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles all database operations"""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)

    # User operations
    def get_user(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Discord ID"""
        try:
            result = (
                self.client.table("users")
                .select("*")
                .eq("discord_id", discord_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user {discord_id}: {e}")
            return None

    def create_user(
        self, discord_id: str, leetcode_username: str
    ) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            user_data = {
                "discord_id": discord_id,
                "leetcode_username": leetcode_username,
                "created_at": datetime.utcnow().isoformat(),
                "monthly_score": 0,
                "weekly_score": 0,
            }
            result = self.client.table("users").insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def update_user_username(self, discord_id: str, new_username: str) -> bool:
        """Update user's Leetcode username"""
        try:
            result = (
                self.client.table("users")
                .update({"leetcode_username": new_username})
                .eq("discord_id", discord_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating username: {e}")
            return False

    def update_user_scores(
        self, discord_id: str, monthly_score: int, weekly_score: int
    ) -> bool:
        """Update user's scores"""
        try:
            result = (
                self.client.table("users")
                .update(
                    {
                        "monthly_score": monthly_score,
                        "weekly_score": weekly_score,
                    }
                )
                .eq("discord_id", discord_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating scores: {e}")
            return False

    # Group operations
    def get_all_groups(self) -> List[Dict[str, Any]]:
        """Get all groups"""
        try:
            result = self.client.table("groups").select("*").execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []

    def create_group(
        self, name: str, channel_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new group"""
        try:
            group_data = {
                "name": name,
                "created_at": datetime.utcnow().isoformat(),
            }
            if channel_id:
                group_data["channel_id"] = channel_id

            result = self.client.table("groups").insert(group_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return None

    def update_group_channel(self, group_id: int, channel_id: str) -> bool:
        """Update group's channel ID"""
        try:
            result = (
                self.client.table("groups")
                .update({"channel_id": channel_id})
                .eq("id", group_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating group channel: {e}")
            return False

    def get_group_members(self, group_id: int) -> List[Dict[str, Any]]:
        """Get members of a specific group"""
        try:
            result = (
                self.client.table("group_members")
                .select("*")
                .eq("group_id", group_id)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Error getting group members: {e}")
            return []

    def add_member_to_group(self, group_id: int, discord_id: str) -> bool:
        """Add member to group"""
        try:
            member_data = {
                "group_id": group_id,
                "discord_id": discord_id,
                "joined_at": datetime.utcnow().isoformat(),
            }
            result = self.client.table("group_members").insert(member_data).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error adding member to group: {e}")
            return False

    def get_user_group(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Get the group that a user belongs to"""
        try:
            result = (
                self.client.table("group_members")
                .select("group_id")
                .eq("discord_id", discord_id)
                .execute()
            )
            if not result.data:
                return None

            group_id = result.data[0]["group_id"]
            group_result = (
                self.client.table("groups").select("*").eq("id", group_id).execute()
            )
            return group_result.data[0] if group_result.data else None
        except Exception as e:
            logger.error(f"Error getting user group: {e}")
            return None

    # Question operations
    def save_daily_question(
        self, question_slug: str, question_title: str, difficulty: str
    ) -> Optional[Dict[str, Any]]:
        """Save daily question to database"""
        try:
            question_data = {
                "question_slug": question_slug,
                "question_title": question_title,
                "difficulty": difficulty,
                "sent_at": datetime.utcnow().isoformat(),
                "timestamp": int(datetime.utcnow().timestamp()),
            }
            result = (
                self.client.table("daily_questions").insert(question_data).execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error saving daily question: {e}")
            return None

    def get_used_question_slugs(self) -> List[str]:
        """Get list of used question slugs"""
        try:
            result = (
                self.client.table("daily_questions").select("question_slug").execute()
            )
            return [q["question_slug"] for q in result.data]
        except Exception as e:
            logger.error(f"Error getting used questions: {e}")
            return []

    # Submission operations
    def save_submission(self, user_id: str, question_id: int, solved: bool) -> bool:
        """Save submission result"""
        try:
            submission_data = {
                "user_id": user_id,
                "question_id": question_id,
                "solved": solved,
                "checked_at": datetime.utcnow().isoformat(),
            }
            result = self.client.table("submissions").insert(submission_data).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error saving submission: {e}")
            return False

    # Leaderboard operations
    def get_monthly_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get monthly global leaderboard"""
        try:
            result = (
                self.client.table("users")
                .select("*")
                .order("monthly_score", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Error getting monthly leaderboard: {e}")
            return []

    def get_group_weekly_leaderboard(self, group_id: int) -> List[Dict[str, Any]]:
        """Get weekly leaderboard for a specific group"""
        try:
            # Get group members
            group_members = self.get_group_members(group_id)
            member_ids = [m["discord_id"] for m in group_members]

            if not member_ids:
                return []

            result = (
                self.client.table("users")
                .select("*")
                .in_("discord_id", member_ids)
                .order("weekly_score", desc=True)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Error getting group weekly leaderboard: {e}")
            return []
