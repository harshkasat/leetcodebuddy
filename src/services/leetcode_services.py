import aiohttp
import random
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class LeetCodeService:
    """Handles LeetCode API interactions"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://leetcode.com/graphql"

    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def validate_username(self, username: str) -> bool:
        """Validate if LeetCode username exists"""
        try:
            query = """
            query userProfile($username: String!) {
                matchedUser(username: $username) {
                    username
                    profile {
                        realName
                        aboutMe
                    }
                }
            }
            """

            variables = {"username": username}
            payload = {"query": query, "variables": variables}

            async with self.session.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                data = await response.json()

                if "data" in data and data["data"]["matchedUser"]:
                    return True
                return False

        except Exception as e:
            logger.error(f"Error validating username {username}: {e}")
            return False

    async def fetch_random_question(
        self, used_slugs: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Fetch a random LeetCode question that hasn't been used"""
        try:
            query = """
            query randomQuestion($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
                questionList(
                    categorySlug: $categorySlug
                    limit: $limit
                    skip: $skip
                    filters: $filters
                ) {
                    total: totalNum
                    questions: data {
                        acRate
                        difficulty
                        freqBar
                        frontendQuestionId: questionFrontendId
                        isFavor
                        paidOnly: isPaidOnly
                        status
                        title
                        titleSlug
                        topicTags {
                            name
                            id
                            slug
                        }
                        hasSolution
                        hasVideoSolution
                    }
                }
            }
            """

            variables = {
                "categorySlug": "",
                "skip": random.randint(0, 2000),
                "limit": 50,
                "filters": {},
            }

            payload = {"query": query, "variables": variables}

            async with self.session.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                data = await response.json()
                questions = data["data"]["questionList"]["questions"]

                # Filter out paid-only and already used questions
                available_questions = [
                    q
                    for q in questions
                    if not q["paidOnly"] and q["titleSlug"] not in used_slugs
                ]

                if not available_questions:
                    logger.warning("No available questions found, retrying...")
                    return await self.fetch_random_question(used_slugs)

                selected_question = random.choice(available_questions)
                return selected_question

        except Exception as e:
            logger.error(f"Error fetching LeetCode question: {e}")
            return None

    async def check_user_submission(
        self, leetcode_username: str, question_slug: str, after_timestamp: int
    ) -> bool:
        """Check if user submitted the question after the given timestamp"""
        try:
            query = """
            query recentAcSubmissions($username: String!) {
                recentAcSubmissionList(username: $username, limit: 100) {
                    title
                    titleSlug
                    timestamp
                }
            }
            """

            variables = {"username": leetcode_username}
            payload = {"query": query, "variables": variables}

            async with self.session.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                data = await response.json()

                if "data" not in data or not data["data"]["recentAcSubmissionList"]:
                    return False

                submissions = data["data"]["recentAcSubmissionList"]

                # Check if question was solved after the timestamp
                for submission in submissions:
                    if (
                        submission["titleSlug"] == question_slug
                        and int(submission["timestamp"]) > after_timestamp
                    ):
                        return True

                return False

        except Exception as e:
            logger.error(f"Error checking submission for {leetcode_username}: {e}")
            return False
