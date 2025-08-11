import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import random
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # Required for member join events
bot = commands.Bot(command_prefix="!", intents=intents)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bot token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MAIN_GUILD_ID = int(os.getenv("MAIN_GUILD_ID"))  # Your main server ID


class LeetcodeUsernameModal(discord.ui.Modal, title="Welcome to Leetcode Buddy! 🧠"):
    def __init__(self, user):
        super().__init__()
        self.user = user

    leetcode_username = discord.ui.TextInput(
        label="Your Leetcode Username",
        placeholder="Enter your Leetcode username here...",
        required=True,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            
            # Defer the response immediately to avoid timeout
            await interaction.response.defer(ephemeral=True)
            user_id = str(self.user.id)
            username = self.leetcode_username.value.strip()

            # Validate Leetcode username by checking if it exists
            is_valid = await leetcode_buddy.validate_leetcode_username(username)
            if not is_valid:
                await interaction.response.send_message(
                    f"❌ The Leetcode username '{username}' doesn't exist or is invalid. Please try again with `!update_username <correct_username>`",
                    ephemeral=True,
                )
                return

            # Check if user already exists
            existing_user = (
                supabase.table("users").select("*").eq("discord_id", user_id).execute()
            )

            if existing_user.data:
                await interaction.response.send_message(
                    "You're already registered! Welcome back! 🎉", ephemeral=True
                )
                return

            # Create new user
            user_data = {
                "discord_id": user_id,
                "leetcode_username": username,
                "created_at": datetime.utcnow().isoformat(),
                "monthly_score": 0,
                "weekly_score": 0,
            }

            result = supabase.table("users").insert(user_data).execute()

            if result.data:
                # Get guild from bot instead of interaction
                guild = bot.get_guild(MAIN_GUILD_ID)
                if not guild:
                    await interaction.response.send_message("❌ Server not found. Please contact admin.", ephemeral=True)
                    return
                print(f"Guild: {guild.name}, ID: {guild.id}")
                # Assign user to a group
                group_info = await assign_user_to_group(self.user, guild)
                
                if not group_info:
                    await interaction.response.send_message("❌ Failed to assign to group. Please try again.", ephemeral=True)
                    return

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

                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "❌ Registration failed. Please try again or contact an admin.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in registration modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred during registration. Please try again.",
                ephemeral=True,
            )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.error(f"Modal error: {error}")
        try:
            # Use followup if the interaction is already deferred
            await interaction.followup.send(
                "❌ Something went wrong. Please try again.", ephemeral=True
            )
        except discord.errors.InteractionResponded:
            # If interaction was already responded to, send a regular message
            await interaction.channel.send(
                f"{interaction.user.mention} ❌ Something went wrong. Please try again."
            )


class WelcomeView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.user = user

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

        modal = LeetcodeUsernameModal(self.user)
        await interaction.response.send_modal(modal)

    async def on_timeout(self):
        # Disable all buttons when timeout occurs
        for item in self.children:
            item.disabled = True


class LeetcodeBuddy:
    def __init__(self):
        self.session = None

    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def validate_leetcode_username(self, username):
        """Validate if Leetcode username exists"""
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
                "https://leetcode.com/graphql",
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

    async def fetch_random_leetcode_question(self):
        """Fetch a random LeetCode question that hasn't been used"""
        try:
            # Check used questions from database
            used_questions = (
                supabase.table("daily_questions").select("question_slug").execute()
            )
            used_slugs = [q["question_slug"] for q in used_questions.data]

            # GraphQL query to get random questions
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
                "https://leetcode.com/graphql",
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
                    return await self.fetch_random_leetcode_question()

                selected_question = random.choice(available_questions)
                return selected_question

        except Exception as e:
            logger.error(f"Error fetching LeetCode question: {e}")
            return None

    async def check_user_submission(
        self, leetcode_username, question_slug, after_timestamp
    ):
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
                "https://leetcode.com/graphql",
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


# Initialize LeetCode buddy
leetcode_buddy = LeetcodeBuddy()


@bot.event
async def on_ready():
    """Bot ready event"""
    print(f"{bot.user} has landed!")
    await leetcode_buddy.init_session()

    # Start scheduled tasks
    daily_question_task.start()
    check_submissions_task.start()


@bot.event
async def on_member_join(member):
    """Handle new member joining the server"""
    try:
        # Check if user is already registered
        user_id = str(member.id)
        existing_user = (
            supabase.table("users").select("*").eq("discord_id", user_id).execute()
        )

        if existing_user.data:
            # User is already registered
            embed = discord.Embed(
                title="Welcome back! 🎉",
                description=f"Hey {member.mention}, you're already registered!",
                color=0x00FF00,
            )
            embed.add_field(
                name="Your Leetcode Username",
                value=existing_user.data[0]["leetcode_username"],
                inline=False,
            )
            embed.add_field(
                name="Quick Commands",
                value="`!profile` - View your stats\n`!leaderboard` - See rankings",
                inline=False,
            )

            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                # If DM fails, send in general channel
                general_channel = discord.utils.get(
                    member.guild.channels, name="general"
                )
                if general_channel:
                    await general_channel.send(embed=embed)
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

        view = WelcomeView(member)

        try:
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            # If DM fails, send in general channel and mention user
            general_channel = discord.utils.get(member.guild.channels, name="general")
            if general_channel:
                await general_channel.send(f"{member.mention}", embed=embed, view=view)

    except Exception as e:
        logger.error(f"Error handling member join: {e}")


async def assign_user_to_group(user, guild):
    """Assign user to a group (max 5 per group)"""
    try:
        if not guild:
            logger.error("Guild is None in assign_user_to_group")
            return None

        # Find available group or create new one
        groups = supabase.table("groups").select("*").execute()

        available_group = None
        for group in groups.data:
            member_count = (
                supabase.table("group_members")
                .select("*")
                .eq("group_id", group["id"])
                .execute()
            )
            if len(member_count.data) < 5:
                available_group = group
                break

        if not available_group:
            # Create new group
            group_data = {
                "name": f"Group-{len(groups.data) + 1}",
                "created_at": datetime.utcnow().isoformat(),
            }
            new_group = supabase.table("groups").insert(group_data).execute()
            available_group = new_group.data[0]

            # Create Discord channel for the group
            category = discord.utils.get(guild.categories, name="Leetcode Groups")
            if not category:
                category = await guild.create_category("Leetcode Groups")

            channel = await guild.create_text_channel(
                available_group["name"].lower().replace(" ", "-"),
                category=category,
                topic=f"Leetcode practice group - {available_group['name']}",
            )

            # Update group with channel ID
            supabase.table("groups").update({"channel_id": str(channel.id)}).eq(
                "id", available_group["id"]
            ).execute()
            available_group["channel_id"] = str(channel.id)

        # Add user to group
        member_data = {
            "group_id": available_group["id"],
            "discord_id": str(user.id),
            "joined_at": datetime.utcnow().isoformat(),
        }
        supabase.table("group_members").insert(member_data).execute()

        # Add user to Discord channel
        channel = guild.get_channel(int(available_group["channel_id"]))
        if channel:
            await channel.set_permissions(user, read_messages=True, send_messages=True, read_message_history=True)

            welcome_embed = discord.Embed(
                title="🎉 New Member Alert!",
                description=f"Welcome {user.mention} to {available_group['name']}!",
                color=0x00FF00,
            )
            welcome_embed.add_field(
                name="Group Info",
                value=f"You're now part of a team! Daily challenges will be posted here at 12 AM UTC.",
                inline=False,
            )
            welcome_embed.add_field(
                name="Good luck!",
                value="Let's code together and build those problem-solving skills! 💪",
                inline=False,
            )

            await channel.send(embed=welcome_embed)

        return {
            'id': available_group['id'],
            'name': available_group['name'], 
            'channel_id': available_group['channel_id']
        }

    except Exception as e:
        logger.error(f"Error assigning user to group: {e}")
        return None


@bot.command(name="update_username")
async def update_username(ctx, new_username: str):
    """Update Leetcode username"""
    try:
        user_id = str(ctx.author.id)

        # Validate new username
        is_valid = await leetcode_buddy.validate_leetcode_username(new_username)
        if not is_valid:
            await ctx.send(
                f"❌ The Leetcode username '{new_username}' doesn't exist or is invalid."
            )
            return

        # Update username
        result = (
            supabase.table("users")
            .update({"leetcode_username": new_username})
            .eq("discord_id", user_id)
            .execute()
        )

        if result.data:
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


@tasks.loop(hours=24)
async def daily_question_task():
    """Send daily question at 12 AM UTC"""
    try:
        # Fetch random question
        question = await leetcode_buddy.fetch_random_leetcode_question()
        if not question:
            logger.error("Failed to fetch question")
            return

        # Save question to database
        question_data = {
            "question_slug": question["titleSlug"],
            "question_title": question["title"],
            "difficulty": question["difficulty"],
            "sent_at": datetime.utcnow().isoformat(),
            "timestamp": int(datetime.utcnow().timestamp()),
        }

        daily_question = (
            supabase.table("daily_questions").insert(question_data).execute()
        )

        # Get all groups and send question
        groups = supabase.table("groups").select("*").execute()
        guild = bot.get_guild(MAIN_GUILD_ID)

        for group in groups.data:
            if group["channel_id"]:
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
                        name="🎯 Points", value="+5 points for solving", inline=False
                    )
                    embed.set_footer(text="Good luck team! 💪")

                    await channel.send("@everyone", embed=embed)

        logger.info(f"Daily question sent: {question['title']}")

    except Exception as e:
        logger.error(f"Error in daily question task: {e}")


@tasks.loop(hours=24)
async def check_submissions_task():
    """Check submissions 24 hours after question was sent"""
    try:
        # Get yesterday's question
        yesterday = datetime.utcnow() - timedelta(days=1)
        question_result = (
            supabase.table("daily_questions")
            .select("*")
            .gte("sent_at", yesterday.date().isoformat())
            .execute()
        )

        if not question_result.data:
            return

        question = question_result.data[0]
        question_timestamp = question["timestamp"]

        # Get all users
        users = supabase.table("users").select("*").execute()

        for user in users.data:
            # Check if user solved the question
            solved = await leetcode_buddy.check_user_submission(
                user["leetcode_username"], question["question_slug"], question_timestamp
            )

            # Save submission result
            submission_data = {
                "user_id": user["discord_id"],
                "question_id": question["id"],
                "solved": solved,
                "checked_at": datetime.utcnow().isoformat(),
            }
            supabase.table("submissions").insert(submission_data).execute()

            # Update user scores if solved
            if solved:
                new_monthly_score = user["monthly_score"] + 5
                new_weekly_score = user["weekly_score"] + 5

                supabase.table("users").update(
                    {
                        "monthly_score": new_monthly_score,
                        "weekly_score": new_weekly_score,
                    }
                ).eq("discord_id", user["discord_id"]).execute()

        logger.info("Submissions checked and scores updated")

    except Exception as e:
        logger.error(f"Error checking submissions: {e}")


# Set task times to run at 12 AM UTC
@daily_question_task.before_loop
async def before_daily_question():
    await bot.wait_until_ready()
    # Calculate seconds until next 12 AM UTC
    now = datetime.utcnow()
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    seconds_until_midnight = (next_midnight - now).total_seconds()
    await asyncio.sleep(seconds_until_midnight)


@check_submissions_task.before_loop
async def before_check_submissions():
    await bot.wait_until_ready()
    # Start checking submissions 1 hour after daily questions (1 AM UTC)
    now = datetime.utcnow()
    next_check_time = (now + timedelta(days=1)).replace(
        hour=1, minute=0, second=0, microsecond=0
    )
    seconds_until_check = (next_check_time - now).total_seconds()
    await asyncio.sleep(seconds_until_check)


@bot.command(name="leaderboard")
async def show_leaderboard(ctx, type_arg: str = "monthly"):
    """Show leaderboard (monthly/weekly)"""
    try:
        if type_arg.lower() == "weekly":
            # Show group weekly leaderboard
            user_id = str(ctx.author.id)

            # Get user's group
            member = (
                supabase.table("group_members")
                .select("group_id")
                .eq("discord_id", user_id)
                .execute()
            )
            if not member.data:
                await ctx.send(
                    "You're not in any group yet. Please complete registration first."
                )
                return

            group_id = member.data[0]["group_id"]

            # Get group members and their scores
            group_members = (
                supabase.table("group_members")
                .select("discord_id")
                .eq("group_id", group_id)
                .execute()
            )
            member_ids = [m["discord_id"] for m in group_members.data]

            users = (
                supabase.table("users")
                .select("*")
                .in_("discord_id", member_ids)
                .order("weekly_score", desc=True)
                .execute()
            )

            embed = discord.Embed(title="🏆 Weekly Group Leaderboard", color=0xFFD700)

        else:
            # Show monthly global leaderboard
            users = (
                supabase.table("users")
                .select("*")
                .order("monthly_score", desc=True)
                .limit(10)
                .execute()
            )
            embed = discord.Embed(title="🌟 Monthly Global Leaderboard", color=0xFF6B6B)

        if not users.data:
            embed.add_field(name="No data", value="No users found", inline=False)
        else:
            leaderboard_text = ""
            for i, user in enumerate(users.data, 1):
                score = (
                    user["weekly_score"]
                    if type_arg.lower() == "weekly"
                    else user["monthly_score"]
                )
                discord_user = bot.get_user(int(user["discord_id"]))
                username = (
                    discord_user.display_name
                    if discord_user
                    else user["leetcode_username"]
                )

                medal = (
                    "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                )
                leaderboard_text += f"{medal} **{username}** - {score} points\n"

            embed.add_field(name="Rankings", value=leaderboard_text, inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Error showing leaderboard: {e}")
        await ctx.send("Failed to fetch leaderboard.")


@bot.command(name="profile")
async def show_profile(ctx):
    """Show user profile"""
    try:
        user_id = str(ctx.author.id)
        user_data = (
            supabase.table("users").select("*").eq("discord_id", user_id).execute()
        )

        if not user_data.data:
            await ctx.send(
                "You're not registered yet. Please complete registration first when you joined the server."
            )
            return

        user = user_data.data[0]

        embed = discord.Embed(
            title=f"Profile: {ctx.author.display_name}", color=0x7289DA
        )
        embed.add_field(
            name="LeetCode Username", value=user["leetcode_username"], inline=True
        )
        embed.add_field(
            name="Monthly Score", value=f"{user['monthly_score']} points", inline=True
        )
        embed.add_field(
            name="Weekly Score", value=f"{user['weekly_score']} points", inline=True
        )
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Error showing profile: {e}")
        await ctx.send("Failed to fetch profile.")


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required argument. Use `!help` for command usage.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("An error occurred while processing the command.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
