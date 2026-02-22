"""
╔══════════════════════════════════════════════════════╗
║           WARRIOR MULTI BOT - VERSION 4.2            ║
║         PROGRAMMED BY SUBHAN | POWERED BY NOOB       ║
╚══════════════════════════════════════════════════════╝

Requirements:
    pip install discord.py aiohttp

Run:
    python warrior_bot.py
"""

import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import json
import os
import time
import itertools
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
TOKEN = os.getenv("TOKEN") # create .env file to save your bot token

# Config in Bot

PREFIX          = "sp"                     # command prefix
TOKENS_FILE     = "bot_tokens.json"             # tokens storage file
WARRIOR_COLOR   = 0xFF0000                      # red theme
SUCCESS_COLOR   = 0x00FF7F
ERROR_COLOR     = 0xFF4444
INFO_COLOR      = 0x00BFFF

# ─────────────────────────────────────────────
#  TOKEN STORAGE HELPERS
# ─────────────────────────────────────────────

def load_tokens() -> dict:
    """Load tokens from JSON file. Returns {name: token}"""
    if not os.path.exists(TOKENS_FILE):
        return {}
    try:
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_tokens(data: dict):
    """Save tokens dict to JSON file."""
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─────────────────────────────────────────────
#  WARRIOR CLIENT
# ─────────────────────────────────────────────

class WarriorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=PREFIX, intents=intents,
                         help_command=None,
                         activity=discord.Activity(
                             type=discord.ActivityType.watching,
                             name="WARRIOR ON TOP"),
                         status=discord.Status.dnd)

        self.activity_messages = itertools.cycle([
            discord.Activity(type=discord.ActivityType.watching, name="SARAIKI PLAYS"),
            discord.Activity(type=discord.ActivityType.watching, name="OFFICAL BOT"),
            discord.Activity(type=discord.ActivityType.watching, name="LATENCY 35ms"),
            discord.Activity(type=discord.ActivityType.watching, name="PREFIX sp"),
            discord.Activity(type=discord.ActivityType.watching, name="POWERED BY SARAIKI"),
            discord.Activity(type=discord.ActivityType.watching, name="PROGRAMMED BY SUBHAN")
        ])

        # {name: discord.Client}  – live VC bots
        self.slave_clients: dict[str, discord.Client] = {}
        self.start_time = datetime.now(timezone.utc)

    async def setup_hook(self):
        self.rotate_activity.start()

    async def on_ready(self):
        print(f"[WARRIOR] Logged in as {self.user} (ID: {self.user.id})")
        print(f"[WARRIOR] Prefix: {PREFIX}")

    @tasks.loop(seconds=15)
    async def rotate_activity(self):
        await self.change_presence(
            status=discord.Status.dnd,
            activity=next(self.activity_messages))

    @rotate_activity.before_loop
    async def before_rotate(self):
        await self.wait_until_ready()

bot = WarriorBot()

# ─────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────

def warrior_embed(title: str, description: str = "", color: int = WARRIOR_COLOR) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color,
                      timestamp=datetime.now(timezone.utc))
    e.set_footer(text="SARAIKI BOT| PROGRAMMED BY SUBHAN")
    return e

async def check_token_valid(token: str, session: aiohttp.ClientSession) -> bool:
    """Returns True if Discord token is valid."""
    headers = {"Authorization": f"Bot {token}",
               "Content-Type": "application/json"}
    try:
        async with session.get("https://discord.com/api/v10/users/@me",
                               headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
            return r.status == 200
    except Exception:
        return False

# ─────────────────────────────────────────────
#  SLAVE BOT HELPER  (for VC join/leave)
# ─────────────────────────────────────────────

async def connect_slave(name: str, token: str, channel: discord.VoiceChannel) -> str:
    """Create a minimal discord.Client, login, join VC. Returns status string."""
    try:
        intents = discord.Intents.default()
        intents.voice_states = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            pass

        # Start client in background without blocking
        asyncio.create_task(client.start(token))
        # Wait for the client to be ready (max 12 sec)
        deadline = asyncio.get_event_loop().time() + 12
        while not client.is_ready():
            if asyncio.get_event_loop().time() > deadline:
                await client.close()
                return f"❌ `{name}` – timeout"
            await asyncio.sleep(0.5)

        vc_channel = client.get_channel(channel.id)
        if vc_channel is None:
            await client.close()
            return f"❌ `{name}` – channel not found"
        await vc_channel.connect()
        bot.slave_clients[name] = client
        return f"✅ `{name}` – joined **{channel.name}**"
    except discord.LoginFailure:
        return f"❌ `{name}` – invalid token"
    except Exception as ex:
        return f"❌ `{name}` – {ex}"

async def disconnect_slave(name: str) -> str:
    client = bot.slave_clients.get(name)
    if not client:
        return f"⚠️ `{name}` – not connected"
    try:
        for vc in client.voice_clients:
            await vc.disconnect(force=True)
        await client.close()
        bot.slave_clients.pop(name, None)
        return f"✅ `{name}` – left VC"
    except Exception as ex:
        return f"❌ `{name}` – {ex}"

# ═══════════════════════════════════════════════════════════
#  VIEWS / BUTTONS
# ═══════════════════════════════════════════════════════════

# ─────────── MAIN PANEL ───────────
class MainPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📊 Bot Status", style=discord.ButtonStyle.blurple, row=0, custom_id="wp_status")
    async def btn_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_status(interaction)

    @discord.ui.button(label="➕ Add Tokens", style=discord.ButtonStyle.green, row=0, custom_id="wp_add")
    async def btn_add(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddTokenModal())

    @discord.ui.button(label="🔍 Check Tokens", style=discord.ButtonStyle.grey, row=0, custom_id="wp_check")
    async def btn_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        await check_tokens_action(interaction)

    @discord.ui.button(label="🗑️ Delete Invalid", style=discord.ButtonStyle.red, row=1, custom_id="wp_del_invalid")
    async def btn_del_invalid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await delete_invalid_action(interaction)

    @discord.ui.button(label="✏️ Edit Tokens", style=discord.ButtonStyle.blurple, row=1, custom_id="wp_edit")
    async def btn_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_edit_panel(interaction)

    @discord.ui.button(label="🎤 Join VC", style=discord.ButtonStyle.green, row=2, custom_id="wp_joinvc")
    async def btn_join_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(JoinVCModal())

    @discord.ui.button(label="🔇 Leave VC", style=discord.ButtonStyle.red, row=2, custom_id="wp_leavevc")
    async def btn_leave_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await leave_all_vc(interaction)

    @discord.ui.button(label="🤖 Bot-wise Join", style=discord.ButtonStyle.blurple, row=3, custom_id="wp_bwjoin")
    async def btn_bw_join(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BotWiseJoinModal())

    @discord.ui.button(label="👋 Bot-wise Leave", style=discord.ButtonStyle.grey, row=3, custom_id="wp_bwleave")
    async def btn_bw_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BotWiseLeaveModal())

    @discord.ui.button(label="🏰 Server Info", style=discord.ButtonStyle.blurple, row=4, custom_id="wp_srvinfo")
    async def btn_server_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_server_info(interaction)

    @discord.ui.button(label="👑 Check Admins", style=discord.ButtonStyle.grey, row=4, custom_id="wp_admins")
    async def btn_admins(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_admins(interaction)

# ─────────── MODALS ───────────

class AddTokenModal(discord.ui.Modal, title="➕ Add Bot Tokens"):
    tokens_input = discord.ui.TextInput(
        label="Tokens (line-wise: Name: Token)",
        style=discord.TextStyle.paragraph,
        placeholder="MyBot1: TOKEN_HERE\nMyBot2: TOKEN_HERE",
        required=True, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_tokens()
        added, skipped, errors = [], [], []
        for line in self.tokens_input.value.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                errors.append(f"`{line[:30]}` – invalid format")
                continue
            name, _, token = line.partition(":")
            name = name.strip()
            token = token.strip()
            if not name or not token:
                errors.append(f"`{line[:30]}` – empty name/token")
                continue
            if name in data:
                skipped.append(f"`{name}`")
            else:
                data[name] = token
                added.append(f"`{name}`")
        save_tokens(data)

        e = warrior_embed("➕ Add Bot Tokens", color=SUCCESS_COLOR)
        e.add_field(name="✅ Added", value=", ".join(added) if added else "None", inline=False)
        e.add_field(name="⚠️ Already Exists", value=", ".join(skipped) if skipped else "None", inline=False)
        if errors:
            e.add_field(name="❌ Errors", value="\n".join(errors), inline=False)
        e.add_field(name="📦 Total Tokens", value=str(len(data)), inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)

class JoinVCModal(discord.ui.Modal, title="🎤 Join VC – All Bots"):
    vc_id = discord.ui.TextInput(label="Voice Channel ID", placeholder="123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            channel = interaction.guild.get_channel(int(self.vc_id.value.strip()))
            if not isinstance(channel, discord.VoiceChannel):
                e = warrior_embed("❌ Error", "Invalid Voice Channel ID.", ERROR_COLOR)
                return await interaction.followup.send(embed=e, ephemeral=True)
        except ValueError:
            e = warrior_embed("❌ Error", "Channel ID must be a number.", ERROR_COLOR)
            return await interaction.followup.send(embed=e, ephemeral=True)

        data = load_tokens()
        if not data:
            e = warrior_embed("⚠️ No Tokens", "Add tokens first.", ERROR_COLOR)
            return await interaction.followup.send(embed=e, ephemeral=True)

        results = []
        for name, token in data.items():
            status = await connect_slave(name, token, channel)
            results.append(status)

        e = warrior_embed("🎤 VC Join Results", f"**Channel:** {channel.name} (`{channel.id}`)\n\n" +
                          "\n".join(results), SUCCESS_COLOR)
        await interaction.followup.send(embed=e, ephemeral=True)

class BotWiseJoinModal(discord.ui.Modal, title="🤖 Bot-wise VC Join"):
    bot_name = discord.ui.TextInput(label="Bot Name", placeholder="MyBot1", required=True)
    vc_id    = discord.ui.TextInput(label="Voice Channel ID", placeholder="123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_tokens()
        name = self.bot_name.value.strip()
        if name not in data:
            e = warrior_embed("❌ Not Found", f"`{name}` token nahi mila.", ERROR_COLOR)
            return await interaction.followup.send(embed=e, ephemeral=True)
        try:
            channel = interaction.guild.get_channel(int(self.vc_id.value.strip()))
            if not isinstance(channel, discord.VoiceChannel):
                raise ValueError
        except ValueError:
            e = warrior_embed("❌ Error", "Invalid Voice Channel ID.", ERROR_COLOR)
            return await interaction.followup.send(embed=e, ephemeral=True)

        status = await connect_slave(name, data[name], channel)
        e = warrior_embed("🤖 Bot-wise Join", status, SUCCESS_COLOR)
        await interaction.followup.send(embed=e, ephemeral=True)

class BotWiseLeaveModal(discord.ui.Modal, title="👋 Bot-wise VC Leave"):
    bot_name = discord.ui.TextInput(label="Bot Name", placeholder="MyBot1", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        name = self.bot_name.value.strip()
        status = await disconnect_slave(name)
        e = warrior_embed("👋 Bot-wise Leave", status, INFO_COLOR)
        await interaction.followup.send(embed=e, ephemeral=True)

# ─────────── EDIT PANEL ───────────

class EditTokenView(discord.ui.View):
    def __init__(self, tokens: dict):
        super().__init__(timeout=120)
        self.tokens = tokens
        names = list(tokens.keys())
        for i, name in enumerate(names[:20]):  # max 20 buttons
            row = i // 5
            btn = discord.ui.Button(label=str(i + 1), style=discord.ButtonStyle.blurple,
                                    custom_id=f"edit_{name}", row=row)
            btn.callback = self._make_callback(name)
            self.add_item(btn)

    def _make_callback(self, name: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(EditSingleTokenModal(name, self.tokens[name]))
        return callback

class EditSingleTokenModal(discord.ui.Modal, title="✏️ Edit / Remove Token"):
    def __init__(self, name: str, token: str):
        super().__init__()
        self.token_name = name
        self.new_name_field = discord.ui.TextInput(
            label="New Name (leave same to keep)", default=name, required=True)
        self.new_token_field = discord.ui.TextInput(
            label="New Token (leave blank to DELETE)", default=token,
            required=False, placeholder="Leave empty to remove this token")
        self.add_item(self.new_name_field)
        self.add_item(self.new_token_field)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_tokens()
        old_name = self.token_name
        new_name  = self.new_name_field.value.strip()
        new_token = self.new_token_field.value.strip()

        if old_name in data:
            del data[old_name]

        if not new_token:
            save_tokens(data)
            e = warrior_embed("🗑️ Token Removed", f"`{old_name}` token remove ho gaya.", INFO_COLOR)
        else:
            data[new_name] = new_token
            save_tokens(data)
            e = warrior_embed("✅ Token Updated",
                              f"**Old Name:** `{old_name}`\n**New Name:** `{new_name}`\n**Token:** `{new_token[:20]}...`",
                              SUCCESS_COLOR)
        await interaction.response.send_message(embed=e, ephemeral=True)

# ═══════════════════════════════════════════════════════════
#  ACTION FUNCTIONS
# ═══════════════════════════════════════════════════════════

async def show_status(interaction: discord.Interaction):
    uptime = datetime.now(timezone.utc) - bot.start_time
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    mins, secs = divmod(rem, 60)
    data = load_tokens()
    guilds   = len(bot.guilds)
    members  = sum(g.member_count or 0 for g in bot.guilds)
    latency  = round(bot.latency * 1000)
    vc_active = len(bot.slave_clients)

    e = warrior_embed("SARAIKI BOT STATUS", color=WARRIOR_COLOR)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    e.add_field(name="🤖 Bot Name",     value=str(bot.user),           inline=True)
    e.add_field(name="🆔 Bot ID",       value=str(bot.user.id),        inline=True)
    e.add_field(name="📡 Ping",         value=f"{latency}ms",          inline=True)
    e.add_field(name="⏱️ Uptime",       value=f"{hours}h {mins}m {secs}s", inline=True)
    e.add_field(name="🏰 Servers",      value=str(guilds),             inline=True)
    e.add_field(name="👥 Members",      value=str(members),            inline=True)
    e.add_field(name="🔑 Saved Tokens", value=str(len(data)),          inline=True)
    e.add_field(name="🎤 VC Bots Active", value=str(vc_active),        inline=True)
    e.add_field(name="⚔️ Version",      value="1.99.9 Alpha",          inline=True)
    await interaction.response.send_message(embed=e, ephemeral=True)

async def check_tokens_action(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_tokens()
    if not data:
        e = warrior_embed("⚠️ No Tokens", "Koi token saved nahi hai. Pehle add karein.", ERROR_COLOR)
        return await interaction.followup.send(embed=e, ephemeral=True)

    working, not_working = [], []
    async with aiohttp.ClientSession() as session:
        tasks_list = [(name, check_token_valid(token, session)) for name, token in data.items()]
        results = await asyncio.gather(*[t[1] for t in tasks_list])
        for (name, _), valid in zip(tasks_list, results):
            (working if valid else not_working).append(name)

    e = warrior_embed("🔍 Token Check Results", color=INFO_COLOR)
    e.add_field(name=f"✅ Working ({len(working)})",
                value="\n".join(f"`{n}`" for n in working) if working else "None", inline=False)
    e.add_field(name=f"❌ Not Working ({len(not_working)})",
                value="\n".join(f"`{n}`" for n in not_working) if not_working else "None", inline=False)
    await interaction.followup.send(embed=e, ephemeral=True)

async def delete_invalid_action(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_tokens()
    if not data:
        e = warrior_embed("⚠️ No Tokens", "Koi token saved nahi hai.", ERROR_COLOR)
        return await interaction.followup.send(embed=e, ephemeral=True)

    deleted = []
    async with aiohttp.ClientSession() as session:
        tasks_list = [(name, token, check_token_valid(token, session)) for name, token in data.items()]
        results = await asyncio.gather(*[t[2] for t in tasks_list])
        new_data = {}
        for (name, token, _), valid in zip(tasks_list, results):
            if valid:
                new_data[name] = token
            else:
                deleted.append(name)
    save_tokens(new_data)

    e = warrior_embed("🗑️ Invalid Tokens Deleted", color=WARRIOR_COLOR)
    e.add_field(name=f"🗑️ Deleted ({len(deleted)})",
                value="\n".join(f"`{n}`" for n in deleted) if deleted else "None", inline=False)
    remaining = "\n".join(f"`{n}`" for n in new_data.keys()) if new_data else "None"
    e.add_field(name=f"✅ Remaining ({len(new_data)})", value=remaining, inline=False)
    await interaction.followup.send(embed=e, ephemeral=True)

async def show_edit_panel(interaction: discord.Interaction):
    data = load_tokens()
    if not data:
        e = warrior_embed("⚠️ No Tokens", "Pehle tokens add karein.", ERROR_COLOR)
        return await interaction.response.send_message(embed=e, ephemeral=True)

    lines = [f"**{i+1}.** `{name}`: `{token[:20]}...`"
             for i, (name, token) in enumerate(data.items())]
    e = warrior_embed("✏️ Edit Tokens",
                      "Neeche buttons se specific token select karein:\n\n" + "\n".join(lines),
                      color=INFO_COLOR)
    view = EditTokenView(data)
    await interaction.response.send_message(embed=e, view=view, ephemeral=True)

async def leave_all_vc(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not bot.slave_clients:
        e = warrior_embed("⚠️ No Active Bots", "Koi bot VC mein nahi hai.", ERROR_COLOR)
        return await interaction.followup.send(embed=e, ephemeral=True)

    results = []
    names = list(bot.slave_clients.keys())
    for name in names:
        status = await disconnect_slave(name)
        results.append(status)

    e = warrior_embed("🔇 All Bots Left VC",
                      "\n".join(results), INFO_COLOR)
    await interaction.followup.send(embed=e, ephemeral=True)

async def show_server_info(interaction: discord.Interaction):
    g = interaction.guild
    e = warrior_embed(f"🏰 Server Info – {g.name}", color=WARRIOR_COLOR)
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    e.add_field(name="🆔 Server ID",        value=str(g.id),                        inline=True)
    e.add_field(name="👑 Owner",            value=g.owner.mention if g.owner else "Unknown", inline=True)
    e.add_field(name="📅 Created",          value=discord.utils.format_dt(g.created_at, "D"), inline=True)
    e.add_field(name="👥 Members",          value=str(g.member_count),              inline=True)
    bots = sum(1 for m in g.members if m.bot)
    e.add_field(name="🤖 Bots",             value=str(bots),                        inline=True)
    e.add_field(name="💬 Text Channels",    value=str(len(g.text_channels)),        inline=True)
    e.add_field(name="🔊 Voice Channels",   value=str(len(g.voice_channels)),       inline=True)
    e.add_field(name="📁 Categories",       value=str(len(g.categories)),           inline=True)
    e.add_field(name="🎭 Roles",            value=str(len(g.roles)),                inline=True)
    e.add_field(name="😀 Emojis",           value=str(len(g.emojis)),               inline=True)
    e.add_field(name="🔒 Verification",     value=str(g.verification_level).title(), inline=True)
    e.add_field(name="💎 Boost Level",      value=f"Level {g.premium_tier}",        inline=True)
    e.add_field(name="🚀 Boosts",           value=str(g.premium_subscription_count), inline=True)
    await interaction.response.send_message(embed=e, ephemeral=True)

async def show_admins(interaction: discord.Interaction):
    g = interaction.guild
    admins = [m for m in g.members if m.guild_permissions.administrator]
    bots_admin   = [m for m in admins if m.bot]
    humans_admin = [m for m in admins if not m.bot]

    e = warrior_embed("👑 Server Administrators", color=WARRIOR_COLOR)
    h_val = "\n".join(f"{m.mention} – `{m.name}`" for m in humans_admin) or "None"
    b_val = "\n".join(f"{m.mention} – `{m.name}`" for m in bots_admin) or "None"
    e.add_field(name=f"👤 Human Admins ({len(humans_admin)})", value=h_val[:1024], inline=False)
    e.add_field(name=f"🤖 Bot Admins ({len(bots_admin)})",    value=b_val[:1024], inline=False)
    await interaction.response.send_message(embed=e, ephemeral=True)

# ═══════════════════════════════════════════════════════════
#  MAIN PANEL COMMAND
# ═══════════════════════════════════════════════════════════

@bot.command(name="")   # "warrior" prefix alone
async def warrior_panel(ctx: commands.Context):
    e = warrior_embed(
        "SARAIKI MULTI BOT – CONTROL PANEL",
        (
            "```\n"
            "╔══════════════════════════════════╗\n"
            "║   SARAIKI MULTI BOT              ║\n"
            "║   PROGRAMMED BY SUBHAN           ║\n"
            "║   POWERED BY ADEEL SARAIKI       ║\n"
            "║   BOT VERSION: 1.99.9 Alpha      ║\n"
            "╚══════════════════════════════════╝\n"
            "```\n"
            "Neeche buttons se koi bhi feature use karein:"
        ),
        color=WARRIOR_COLOR
    )
    e.add_field(name="📊 Bot Status",       value="Bot ka poora status dekhen",       inline=True)
    e.add_field(name="➕ Add Tokens",       value="Line-wise tokens add karein",       inline=True)
    e.add_field(name="🔍 Check Tokens",     value="Valid/invalid tokens check karein", inline=True)
    e.add_field(name="🗑️ Delete Invalid",   value="Invalid tokens auto-delete karein", inline=True)
    e.add_field(name="✏️ Edit Tokens",      value="Specific token edit/remove karein", inline=True)
    e.add_field(name="🎤 Join VC",          value="Sab bots VC join karen",            inline=True)
    e.add_field(name="🔇 Leave VC",         value="Sab bots VC leave karen",           inline=True)
    e.add_field(name="🤖 Bot-wise Join",    value="Specific bot VC join kraye",        inline=True)
    e.add_field(name="👋 Bot-wise Leave",   value="Specific bot VC leave kraye",       inline=True)
    e.add_field(name="🏰 Server Info",      value="Server ki poori info dekhen",       inline=True)
    e.add_field(name="👑 Check Admins",     value="Server ke admins list dekhen",      inline=True)
    e.set_image(url="https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUydHZkeHF6bGpuN2tudzJlc3k2c3lwMjhqN2VxMzk2aXkzNnpjbHB6MSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xXFmSTrN8GZMs/giphy.gif")  # optional banner
    await ctx.send(embed=e, view=MainPanel())

# ─── prefix "sp" triggers the panel ───
@bot.listen("on_message")
async def on_warrior_call(message: discord.Message):
    if message.author.bot:
        return
    if message.content.strip().lower() == "adeel":
        ctx = await bot.get_context(message)
        await warrior_panel(ctx)

# ═══════════════════════════════════════════════════════════
#  MODERATION COMMANDS
# ═══════════════════════════════════════════════════════════

def mod_embed(title: str, member: discord.Member, reason: str, moderator: discord.Member, color: int = WARRIOR_COLOR) -> discord.Embed:
    e = discord.Embed(title=f"⚔️ {title}", color=color, timestamp=datetime.now(timezone.utc))
    e.add_field(name="👤 Member",    value=f"{member.mention}\n`{member}`", inline=True)
    e.add_field(name="📋 Reason",    value=reason or "No reason provided",  inline=True)
    e.add_field(name="🔨 Action by", value=f"{moderator.mention}\n`{moderator}`", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="SARAIKI BOT")
    return e

# BAN
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def warrior_ban(ctx: commands.Context, member: discord.Member, *, reason: str = None):
    try:
        await member.ban(reason=reason)
        e = mod_embed("SARAIKI BAN SYSTEM", member, reason, ctx.author, color=0xFF2222)
        e.description = f"🔨 {member.mention} (`{member.name}`) ko ban kar diya gaya!"
        await ctx.send(embed=e)
    except discord.Forbidden:
        await ctx.send(embed=warrior_embed("❌ Permission Error", "Mujhe is member ko ban karne ki permission nahi hai.", ERROR_COLOR))
    except Exception as ex:
        await ctx.send(embed=warrior_embed("❌ Error", str(ex), ERROR_COLOR))

@warrior_ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=warrior_embed("❌ Member Not Found", "Sahi member mention ya ID dein.", ERROR_COLOR))
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=warrior_embed("❌ No Permission", "Aapke paas ban karne ki permission nahi.", ERROR_COLOR))

# KICK
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def warrior_kick(ctx: commands.Context, member: discord.Member, *, reason: str = None):
    try:
        await member.kick(reason=reason)
        e = mod_embed("SARAIKI KICK SYSTEM", member, reason, ctx.author, color=0xFF8800)
        e.description = f"👢 {member.mention} (`{member.name}`) ko kick kar diya gaya!"
        await ctx.send(embed=e)
    except discord.Forbidden:
        await ctx.send(embed=warrior_embed("❌ Permission Error", "Mujhe kick karne ki permission nahi.", ERROR_COLOR))
    except Exception as ex:
        await ctx.send(embed=warrior_embed("❌ Error", str(ex), ERROR_COLOR))

@warrior_kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=warrior_embed("❌ Member Not Found", "Sahi member mention ya ID dein.", ERROR_COLOR))
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=warrior_embed("❌ No Permission", "Aapke paas kick karne ki permission nahi.", ERROR_COLOR))

# TIMEOUT
@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def warrior_timeout(ctx: commands.Context, member: discord.Member, duration: str = "10min", *, reason: str = None):
    # Parse duration string like 10min, 20min, 1h, 30s
    import re
    match = re.fullmatch(r"(\d+)(min|h|s|d)", duration.lower())
    if not match:
        return await ctx.send(embed=warrior_embed("❌ Invalid Duration",
            "Format: `10min`, `1h`, `30s`, `1d`", ERROR_COLOR))
    amount, unit = int(match.group(1)), match.group(2)
    seconds = {"s": 1, "min": 60, "h": 3600, "d": 86400}[unit] * amount

    if seconds > 2419200:  # 28 days Discord limit
        return await ctx.send(embed=warrior_embed("❌ Too Long", "Max timeout 28 days hai.", ERROR_COLOR))

    until = discord.utils.utcnow() + timedelta(seconds=seconds)
    try:
        await member.timeout(until, reason=reason)
        e = mod_embed("SARAIKI TIMEOUT SYSTEM", member, reason, ctx.author, color=0xFFAA00)
        e.description = f"⏱️ {member.mention} (`{member.name}`) ko `{duration}` ke liye timeout diya gaya!"
        await ctx.send(embed=e)
    except discord.Forbidden:
        await ctx.send(embed=warrior_embed("❌ Permission Error", "Mujhe timeout karne ki permission nahi.", ERROR_COLOR))
    except Exception as ex:
        await ctx.send(embed=warrior_embed("❌ Error", str(ex), ERROR_COLOR))

@warrior_timeout.error
async def timeout_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=warrior_embed("❌ Member Not Found", "Sahi member mention ya ID dein.", ERROR_COLOR))
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=warrior_embed("❌ No Permission", "Aapke paas timeout karne ki permission nahi.", ERROR_COLOR))

# CLEAN CHAT
@bot.command(name="CleanChat")
@commands.has_permissions(manage_messages=True)
async def warrior_clean(ctx: commands.Context, amount: int = 10):
    if amount < 1 or amount > 1000:
        return await ctx.send(embed=warrior_embed("❌ Invalid Amount", "1 se 1000 ke beech number dein.", ERROR_COLOR))
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for the command message
        count = len(deleted) - 1
        e = warrior_embed("🧹 SARAIKI CLEAN SYSTEM", color=SUCCESS_COLOR)
        e.description = f"✅ **{count}** messages successfully delete ho gaye!"
        e.add_field(name="📢 Channel", value=ctx.channel.mention, inline=True)
        e.add_field(name="🔨 By",      value=ctx.author.mention,  inline=True)
        e.add_field(name="🗑️ Deleted", value=str(count),          inline=True)
        e.set_footer(text="SARAIKI BOT")
        msg = await ctx.send(embed=e)
        await asyncio.sleep(5)
        await msg.delete()
    except discord.Forbidden:
        await ctx.send(embed=warrior_embed("❌ Permission Error", "Mujhe messages delete karne ki permission nahi.", ERROR_COLOR))
    except Exception as ex:
        await ctx.send(embed=warrior_embed("❌ Error", str(ex), ERROR_COLOR))

@warrior_clean.error
async def clean_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=warrior_embed("❌ No Permission", "Aapke paas manage messages ki permission nahi.", ERROR_COLOR))

# ═══════════════════════════════════════════════════════════
#  GLOBAL ERROR HANDLER
# ═══════════════════════════════════════════════════════════

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return  # ignore unknown commands silently
    if isinstance(error, commands.NoPrivateMessage):
        return await ctx.send(embed=warrior_embed("❌ Error", "Yeh command server mein use karein.", ERROR_COLOR))
    if isinstance(error, commands.BotMissingPermissions):
        perms = ", ".join(error.missing_permissions)
        return await ctx.send(embed=warrior_embed("❌ Bot Permission Error",
            f"Mujhe yeh permissions chahiye: `{perms}`", ERROR_COLOR))
    # Log unexpected errors
    print(f"[ERROR] Command: {ctx.command} | Error: {error}")

# ═══════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if TOKEN == "YOUR_MAIN_BOT_TOKEN_HERE":
        print("⚠️  WARRIOR BOT: warrior_bot.py mein BOT_TOKEN set karein!")
    else:
        bot.run(TOKEN, log_handler=None)Bot ki Key set karein!")
    else:
        bot.run(TOKEN, log_handler=None)
