import os
import aiohttp
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv

load_dotenv()

# CONFIG
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHECK_SECONDS = int(os.getenv("CHECK_SECONDS", 5))

# DISCORD SETUP
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# TRACKING VARIABLES
tracked_username = None
tracked_user_id = None
last_status = None
last_place_id = None
check_count = 0

# GET ROBLOX USER ID
async def get_roblox_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={
            "usernames": [username],
            "excludeBannedUsers": True
        }) as response:
            data = await response.json()

    if not data["data"]:
        raise ValueError("Roblox user not found")

    return data["data"][0]["id"]

# GET ROBLOX PRESENCE
async def get_presence(user_id):
    url = "https://presence.roblox.com/v1/presence/users"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"userIds": [user_id]}) as response:
            data = await response.json()

    presence = data["userPresences"][0]

    return {
        "status": presence["userPresenceType"],
        "place_id": presence.get("placeId"),
        "last_location": presence.get("lastLocation", "Unknown")
    }

# BOT READY
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.change_presence(
        activity=discord.Game(name="Waiting for !check 👀")
    )

    if not track_user.is_running():
        track_user.start()

# COMMAND TO TRACK USER
@bot.command()
async def check(ctx, username):
    global tracked_username
    global tracked_user_id
    global last_status
    global last_place_id

    try:
        user_id = await get_roblox_user_id(username)

        tracked_username = username
        tracked_user_id = user_id

        # RESET STATES
        last_status = None
        last_place_id = None

        await ctx.send(
            f"✅ Now tracking Roblox user: **{username}**"
        )

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# TRACK LOOP
@tasks.loop(seconds=CHECK_SECONDS)
async def track_user():
    global tracked_username
    global tracked_user_id
    global last_status
    global last_place_id
    global check_count

    if tracked_user_id is None:
        return

    channel = bot.get_channel(CHANNEL_ID)

    try:
        presence = await get_presence(tracked_user_id)

        status = presence["status"]
        place_id = presence["place_id"]
        location = presence["last_location"]

        check_count += 1

        print(
            f"[{check_count}] {tracked_username} | "
            f"Status: {status} | Game: {location}"
        )

        # UPDATE BOT STATUS
        try:
            await bot.change_presence(
                activity=discord.Game(
                    name=f"{tracked_username}: {location}"
                )
            )
        except:
            pass

        # ONLINE
        if status == 1 and last_status == 0:
            await channel.send(
                f"🟢 **{tracked_username} is online!**"
            )

        # JOINED GAME
        elif status == 2 and last_status != 2:
            await channel.send(
                f"🎮 **{tracked_username} joined a game:** {location}"
            )

        # SWITCHED GAMES
        elif (
            status == 2
            and last_status == 2
            and place_id != last_place_id
        ):
            await channel.send(
                f"🔄 **{tracked_username} switched games:** {location}"
            )

        # LEFT GAME
        elif status == 1 and last_status == 2:
            await channel.send(
                f"↩️ **{tracked_username} left the game.**"
            )

        # OFFLINE
        elif status == 0 and last_status != 0:
            await channel.send(
                f"🔴 **{tracked_username} went offline.**"
            )

        last_status = status
        last_place_id = place_id

    except Exception as e:
        print("Tracking Error:", e)

# START BOT
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN is not set!")

bot.run(TOKEN)
