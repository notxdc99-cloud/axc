import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from db import init_db, has_active_access, create_payment_request

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID", "").strip()
PRICE = int(os.getenv("PRICE_INR", "99"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!axc ", intents=intents)

def access_message():
    return f"AXC BOT premium access costs ₹{PRICE}. Open the dashboard, submit your payment reference, and wait for manual admin approval."

@bot.event
async def on_ready():
    init_db()
    if GUILD_ID.isdigit():
        guild = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    print(f"AXC BOT online as {bot.user}")

@bot.tree.command(name="pay", description="View AXC BOT payment instructions")
async def pay(interaction: discord.Interaction):
    url = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    await interaction.response.send_message(
        f"**AXC BOT Premium — ₹{PRICE}**\n"
        f"1. Open {url}/pay\n"
        "2. Scan the displayed QR and pay using your UPI app.\n"
        "3. Submit your UPI reference on the page.\n"
        "4. Wait for the admin to verify and approve your request.\n"
        "Access is not granted by submitting a screenshot/reference alone.",
        ephemeral=True
    )

@bot.tree.command(name="premium", description="Check your AXC BOT premium access")
async def premium(interaction: discord.Interaction):
    if has_active_access(interaction.user.id):
        await interaction.response.send_message("Your AXC BOT premium access is active.", ephemeral=True)
    else:
        await interaction.response.send_message(access_message(), ephemeral=True)

@bot.tree.command(name="giveaway", description="Create a demo giveaway (premium access required)")
@app_commands.describe(prize="Prize name", duration_minutes="Duration in minutes")
async def giveaway(interaction: discord.Interaction, prize: str, duration_minutes: app_commands.Range[int, 1, 10080]):
    if not has_active_access(interaction.user.id):
        await interaction.response.send_message(access_message() + "\nUse `/pay` to continue.", ephemeral=True)
        return
    embed = discord.Embed(title="🎉 AXC BOT Giveaway", description=f"**Prize:** {discord.utils.escape_markdown(prize)}\n**Duration:** {duration_minutes} minutes\n\nThis is a giveaway announcement demo.", color=0x8B5CF6)
    embed.set_footer(text="AXC BOT")
    await interaction.response.send_message(embed=embed)

if not TOKEN:
    raise SystemExit("Set DISCORD_TOKEN in your .env file before starting the bot.")
bot.run(TOKEN)
