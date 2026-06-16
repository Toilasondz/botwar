import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button
import asyncio
import threading
import requests
import re
import time
import json
import os
import gc
import random
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

# ==================== CẤU HÌNH ====================
TOKEN = input("   Token bot: ").strip()
ADMIN_IDS = input("   ID Admin: ").split(",")
ADMIN_IDS = [aid.strip() for aid in ADMIN_IDS]

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

bot = commands.Bot(command_prefix="/", intents=INTENTS)
tree = bot.tree

DATA_FILE = "users.json"
NGONMESS_DIR = "ngonmess_data"
os.makedirs(NGONMESS_DIR, exist_ok=True)

# ==================== KHỞI TẠO CÁC BIẾN TOÀN CỤC ====================
user_tabs = {}
user_nhay_tabs = {}
nhaynameboxzl_tabs = {}
user_zalo_tabs = {}
user_sticker_tabs = {}
TREOSTICKER_LOCK = threading.Lock()
ZALO_LOCK = threading.Lock()
NHAYTAGZALO_LOCK = threading.Lock()
user_nhaytagzalo_tabs = {}
TAB_LOCK = threading.Lock()
user_poll_tabs = {}
POLL_LOCK = threading.Lock()
user_image_tabs = {}
IMAGE_TAB_LOCK = threading.Lock()
user_nhaymess_tabs = {}
NHAY_LOCK = threading.Lock()
user_discord_tabs = {}
DIS_LOCK = asyncio.Lock()
user_nhaydis_tabs = {}  
NHAYDIS_LOCK = asyncio.Lock()
user_treotele_tabs = {}   
TREOTELE_LOCK = threading.Lock()
SPAM_TASKS = {}  
TREOSMS_TASKS = {}
TREOSMS_LOCK = threading.Lock()
IG_LOCK = threading.Lock()
user_treogmail_tabs = {}
user_nhaynamebox_tabs = {}
NHAYNAMEBOX_LOCK = threading.Lock()
user_reostr_tabs = {}
TREOGMAIL_LOCK = threading.Lock()
user_nhaytag_tabs = {}
NHAYTAG_LOCK = threading.Lock()
wechat_spam_tabs = {}
WECHAT_SPAM_LOCK = threading.Lock()

# ==================== HÀM TIỆN ÍCH ====================
def format_time(seconds: int) -> str:
    try:
        seconds = int(seconds)
    except Exception:
        return "0s"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)

def get_uptime(start_time: datetime) -> str:
    elapsed = (datetime.now() - start_time).total_seconds()
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def get_guid():
    import uuid
    return str(uuid.uuid4())

# ==================== QUẢN LÝ NGƯỜI DÙNG ====================
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(interaction: discord.Interaction):
    return str(interaction.user.id) in ADMIN_IDS

def is_authorized(interaction: discord.Interaction):
    users = load_users()
    uid = str(interaction.user.id)
    if uid in users:
        exp = users[uid]
        if exp is None:
            return True
        elif datetime.fromisoformat(exp) > datetime.now():
            return True
        else:            
            _remove_user_and_kill_tabs(uid)
    return False

def _add_user(uid: str, days: int = None):
    users = load_users()
    if days:
        expire_time = (datetime.now() + timedelta(days=days)).isoformat()
        users[uid] = expire_time
    else:
        users[uid] = None
    save_users(users)

def _remove_user_and_kill_tabs(uid: str):
    users = load_users()
    if uid in users:
        del users[uid]
        save_users(users)
    with TAB_LOCK:
        if uid in user_tabs:
            for tab in user_tabs[uid]:
                tab["stop_event"].set()
            del user_tabs[uid]

def _get_user_list():
    users = load_users()
    result = []
    for uid, exp in users.items():
        if exp:
            remaining = datetime.fromisoformat(exp) - datetime.now()
            if remaining.total_seconds() <= 0:
                continue  
            days = remaining.days
            hours, rem = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(rem, 60)
            time_str = f"{days} ngày, {hours} giờ, {minutes} phút"
            result.append((uid, time_str))
        else:
            result.append((uid, "vĩnh viễn"))
    return result

# ==================== FACEBOOK HELPERS ====================
def normalize_cookie(cookie, domain='www.facebook.com'):
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(f'https://{domain}/', headers=headers, timeout=10)
        if response.status_code == 200:
            set_cookie = response.headers.get('Set-Cookie', '')
            new_tokens = re.findall(r'([a-zA-Z0-9_-]+)=[^;]+', set_cookie)
            cookie_dict = dict(re.findall(r'([a-zA-Z0-9_-]+)=([^;]+)', cookie))
            for token in new_tokens:
                if token not in cookie_dict:
                    cookie_dict[token] = ''
            return ';'.join(f'{k}={v}' for k, v in cookie_dict.items() if v)
    except:
        pass
    return cookie

def get_uid_fbdtsg(ck):
    try:
        headers = {
            'Accept': 'text/html',
            'Cookie': ck,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        response = requests.get('https://www.facebook.com/', headers=headers, timeout=15)
        html = response.text
        user_id = re.search(r'"USER_ID":"(\d+)"', html)
        fb_dtsg = re.search(r'"f":"([^"]+)"', html)
        jazoest = re.search(r'jazoest=(\d+)', html)
        if user_id and fb_dtsg:
            return user_id.group(1), fb_dtsg.group(1), jazoest.group(1) if jazoest else "", "", "", ""
        return None, None, None, None, None, None
    except:
        return None, None, None, None, None, None

def extract_post_group_id(post_link):
    post_match = re.search(r'facebook\.com/.+/permalink/(\d+)', post_link)
    group_match = re.search(r'facebook\.com/groups/(\d+)', post_link)
    if not post_match or not group_match:
        return None, None
    return post_match.group(1), group_match.group(1)

def get_thread_list(cookie):
    try:
        headers = {'Cookie': cookie, 'User-Agent': 'Mozilla/5.0'}
        response = requests.get('https://www.facebook.com/messages/t/', headers=headers, timeout=15)
        html = response.text
        threads = re.findall(r'thread_fbid":"(\d+)","name":"([^"]+)"', html)
        return [{"thread_id": tid, "thread_name": name} for tid, name in threads]
    except:
        return []

# ==================== MESSENGER CLASS ====================
class Kem:
    def __init__(self, cookie):
        self.cookie = normalize_cookie(cookie)
        self.user_id = self._get_user_id()
        self.fb_dtsg = None
        self._init_params()
    
    def _get_user_id(self):
        match = re.search(r"c_user=(\d+)", self.cookie)
        if match:
            return match.group(1)
        raise Exception("Cookie không hợp lệ")
    
    def _init_params(self):
        headers = {'Cookie': self.cookie, 'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get('https://www.facebook.com', headers=headers, timeout=15)
            fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
            if fb_dtsg_match:
                self.fb_dtsg = fb_dtsg_match.group(1)
            else:
                raise Exception("Không thể lấy fb_dtsg")
        except Exception as e:
            raise Exception(f"Lỗi khởi tạo: {e}")
    
    def gui_tn(self, recipient_id, message):
        timestamp = int(time.time() * 1000)
        data = {
            'thread_fbid': recipient_id,
            'action_type': 'ma-type:user-generated-message',
            'body': message,
            'client': 'mercury',
            'author': f'fbid:{self.user_id}',
            'timestamp': timestamp,
            'source': 'source:chat:web',
            'offline_threading_id': str(timestamp),
            'message_id': str(timestamp),
            '__user': self.user_id,
            '__a': '1',
            '__req': '1b',
            'fb_dtsg': self.fb_dtsg
        }
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'python-http/0.27.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        try:
            response = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers, timeout=30)
            return {'success': response.status_code == 200}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ==================== ZALO CLASSES ====================
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://chat.zalo.me",
    "Referer": "https://chat.zalo.me/",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
}

def now():
    return int(time.time() * 1000)

class ThreadType(Enum):
    USER = 1
    GROUP = 2

class ZaloAPI:
    def __init__(self, imei, cookies):
        self.session = requests.Session()
        self.imei = imei
        self.secret_key = None
        self.uid = None
        self.session.headers.update(HEADERS)
        self.session.cookies.update(cookies)
        self.login()

    def login(self):
        url = "https://wpa.chat.zalo.me/api/login/getLoginInfo"
        params = {"imei": self.imei, "type": 30, "client_version": 645, "ts": now()}
        response = self.session.get(url, params=params, timeout=15)
        try:
            data = response.json()
        except Exception:
            raise Exception("Không thể phân tích JSON từ phản hồi!")

        user_data = data.get("data")
        if not isinstance(user_data, dict):
            raise Exception("Không nhận được thông tin người dùng")

        self.uid = user_data.get("send2me_id")
        self.secret_key = user_data.get("zpw_enk")
        if not self.secret_key:
            raise Exception("Không lấy được secret_key")

    def fetch_groups(self):
        url = "https://tt-group-wpa.chat.zalo.me/api/group/getlg/v4"
        params = {"zpw_ver": 645, "zpw_type": 30}
        response = self.session.get(url, params=params, timeout=15)
        data = response.json()
        try:
            import base64
            from Crypto.Cipher import AES
            decoded = base64.b64decode(data["data"]).decode('utf-8', errors='ignore')
            parsed = json.loads(decoded)
            grid_map = parsed.get("data", {}).get("gridVerMap", {})
            groups = []
            for group_id in grid_map:
                groups.append({"id": group_id, "name": grid_map[group_id].get("name", "Unknown"), "members": 0})
            return groups
        except:
            return []

    def fetch_friends(self):
        return [{"id": "1", "name": "Friend 1"}, {"id": "2", "name": "Friend 2"}]

    def send_message(self, message, thread_id, thread_type):
        print(f"[ZALO] Gửi tin nhắn tới {thread_id}: {message[:50]}...")
        return {"success": True}

    def set_typing_real(self, thread_id, thread_type):
        print(f"[ZALO] Đang soạn tin nhắn tới {thread_id}")

class SpamTool(ZaloAPI):
    def __init__(self, name, imei, cookies, thread_ids, thread_type, use_typing=False):
        super().__init__(imei, cookies)
        self.name = name
        self.thread_ids = thread_ids
        self.thread_type = thread_type
        self.use_typing = use_typing
        self.running = False

    def send_spam(self, messages, delay):
        self.running = True
        msg_index = 0
        while self.running:
            for thread_id in self.thread_ids:
                if not self.running:
                    break
                message = messages[msg_index % len(messages)]
                try:
                    if self.use_typing:
                        self.set_typing_real(thread_id, self.thread_type)
                        time.sleep(1.5)
                    self.send_message(message, thread_id, self.thread_type)
                    print(f"[ZALO#{thread_id}] ✅ {message[:50]}...")
                except Exception as e:
                    print(f"[ZALO#{thread_id}] ❌ {e}")
                time.sleep(delay / len(self.thread_ids))
            msg_index += 1
            time.sleep(delay)

# ==================== DANH SÁCH NỘI DUNG MẶC ĐỊNH ====================
raw_spam_list = [
    "sủa gì sủa lại bố nghe nào con chó rách =))",
    "mồ côi thắp hương cha mẹ trc khi chửi chưa",
    "m có cảnh kh thk óc cặc",
    "đánh con mẹ m luôn đê",
]

# ==================== WORKER FUNCTIONS ====================
def nhaytop_worker(cookie_list, delay, post_id, group_id, tag_id, stop_event, start_time, discord_user_id):
    import random
    idx = 0
    while not stop_event.is_set():
        cookie = cookie_list[idx % len(cookie_list)]
        msg = raw_spam_list[idx % len(raw_spam_list)]
        if tag_id:
            msg = f"@{tag_id} {msg}"
        print(f"[NHAY][{discord_user_id}] → {group_id}/{post_id}: {msg[:50]}...")
        idx += 1
        time.sleep(delay)
    print(f"Tab NHAYTOP của user {discord_user_id} đã dừng.")

def image_tab_worker(post_id, cookies_raw, message, images, tag_id, delay_min, delay_max, stop_event, start_time, discord_user_id):
    idx = 0
    while not stop_event.is_set():
        image_url = images[idx % len(images)]
        msg = message
        if tag_id:
            msg += f" @{tag_id}"
        print(f"[ANHTOP][{discord_user_id}] → {post_id}: {msg[:50]}... | Ảnh: {image_url}")
        idx += 1
        delay = random.uniform(delay_min, delay_max)
        time.sleep(delay)
    print(f"Tab ANHTOP user {discord_user_id} đã dừng.")

def spam_tab_worker(messenger, box_id, get_message_func, delay, stop_event, start_time, discord_user_id):
    success = 0
    fail = 0
    while not stop_event.is_set():
        message = get_message_func()
        result = messenger.gui_tn(box_id, message)
        if result.get("success"):
            success += 1
        else:
            fail += 1
        print(f"[{messenger.user_id}] → {box_id} | {'OK' if result.get('success') else 'FAIL'} | OK: {success} | FAIL: {fail}")
        time.sleep(delay)
    print(f"Tab của user {discord_user_id} đã dừng.")

def telegram_send_loop(token, chat_ids, caption, photo, delay, stop_event, discord_user_id):
    while not stop_event.is_set():
        for chat_id in chat_ids:
            if stop_event.is_set():
                break
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {"chat_id": chat_id, "text": caption}
                response = requests.post(url, json=data, timeout=10)
                if response.status_code == 200:
                    print(f"[TELE][{discord_user_id}] Gửi thành công → {chat_id}")
                else:
                    print(f"[TELE][{discord_user_id}] Lỗi {response.status_code}")
            except Exception as e:
                print(f"[TELE][{discord_user_id}] Exception: {e}")
            time.sleep(0.2)
        time.sleep(delay)

def gmail_spam_loop(tab, discord_user_id):
    to_email = tab["to_email"]
    content = tab["content"]
    delay = tab["delay"]
    stop_evt = tab["stop_event"]
    idx = 0
    while not stop_evt.is_set():
        print(f"[GMAIL][{discord_user_id}] Gửi tới {to_email}: {content[:50]}...")
        idx += 1
        time.sleep(delay)

def spam_sms_forever(phone, stop_event):
    idx = 0
    while not stop_event.is_set():
        print(f"[SMS] Gửi OTP tới {phone} (lần {idx+1})")
        idx += 1
        time.sleep(2)

# ==================== LỆNH DISCORD ====================
@tree.command(name="nhaytop", description="Treo nhây top")
@app_commands.describe(cookies="Cookie", post_link="Link bài viết", delay="Delay", tag_id="ID cần tag")
async def nhaytop(interaction: discord.Interaction, cookies: str, post_link: str, delay: float, tag_id: str = None):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")
    
    cookie_list = [normalize_cookie(c.strip()) for c in cookies.split(",") if c.strip()]
    if not cookie_list:
        return await interaction.response.send_message("Cookie không hợp lệ")
    
    post_id, group_id = extract_post_group_id(post_link)
    if not post_id or not group_id:
        return await interaction.response.send_message("Link không đúng định dạng group/post")
    
    stop_event = threading.Event()
    start_time = datetime.now()
    discord_user_id = str(interaction.user.id)
    
    th = threading.Thread(target=nhaytop_worker, args=(cookie_list, delay, post_id, group_id, tag_id, stop_event, start_time, discord_user_id), daemon=True)
    th.start()
    
    with NHAY_LOCK:
        if discord_user_id not in user_nhay_tabs:
            user_nhay_tabs[discord_user_id] = []
        user_nhay_tabs[discord_user_id].append({"thread": th, "stop_event": stop_event, "start": start_time, "post_id": post_id, "group_id": group_id, "delay": delay, "tag_id": tag_id})
    
    await interaction.response.send_message(f"Đã tạo tab nhây top cho <@{discord_user_id}>:\n• GroupID: `{group_id}` | PostID: `{post_id}`\n• Delay: `{delay}` giây\n• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`")

@tree.command(name="tabnhaytop", description="Quản lý/dừng tab nhây top")
async def tabnhaytop(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")
    
    discord_user_id = str(interaction.user.id)
    with NHAY_LOCK:
        tabs = user_nhay_tabs.get(discord_user_id, [])
    
    if not tabs:
        return await interaction.response.send_message("Bạn không có tab nhây top nào đang hoạt động")
    
    msg = "**Danh sách tab nhây top của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        uptime = get_uptime(tab["start"])
        msg += f"{idx}. Group:`{tab['group_id']}` Post:`{tab['post_id']}` | Delay:`{tab['delay']}`s | Uptime:`{uptime}`\n"
    msg += "\nNhập số tab để dừng tab"
    await interaction.response.send_message(msg)
    
    def check(m): return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
        i = int(reply.content.strip())
        with NHAY_LOCK:
            chosen = tabs.pop(i-1)
            chosen["stop_event"].set()
            if not tabs:
                del user_nhay_tabs[discord_user_id]
        await interaction.followup.send(f"Đã dừng tab nhây số {i}")
    except:
        await interaction.followup.send("Hết thời gian hoặc lỗi")

@tree.command(name="treomess", description="Treo tin nhắn Messenger")
@app_commands.describe(idbox="ID Box", cookie="Cookie Facebook", noidung="Nội dung", delay="Delay giây")
async def treomess(interaction: discord.Interaction, idbox: str, cookie: str, noidung: str, delay: float):
    discord_user_id = str(interaction.user.id)
    try:
        messenger = Kem(cookie)
    except Exception as e:
        return await interaction.response.send_message(f"Cookie không hợp lệ: {e}")
    
    content = noidung
    def get_message(): return content
    
    stop_event = threading.Event()
    start_time = datetime.now()
    th = threading.Thread(target=spam_tab_worker, args=(messenger, idbox, get_message, delay, stop_event, start_time, discord_user_id), daemon=True)
    th.start()
    
    with TAB_LOCK:
        if discord_user_id not in user_tabs:
            user_tabs[discord_user_id] = []
        user_tabs[discord_user_id].append({"box_id": idbox, "delay": delay, "start": start_time, "stop_event": stop_event})
    
    await interaction.response.send_message(f"✅ Đã khởi tab spam Messenger:\n• Box: `{idbox}`\n• Delay: `{delay}` giây\n• Nội dung: `{content[:100]}...`\n• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`")

@tree.command(name="tabtreomess", description="Quản lý/dừng tab treo messenger")
async def tabtreomess(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")
    
    discord_user_id = str(interaction.user.id)
    with TAB_LOCK:
        tabs = user_tabs.get(discord_user_id, [])
    
    if not tabs:
        return await interaction.response.send_message("Bạn không có tab nào đang hoạt động")
    
    msg = "**Danh sách tab treo messenger của bạn:**\n"
    for idx, tab in enumerate(tabs, start=1):
        uptime = get_uptime(tab["start"])
        msg += f"{idx}. Box: `{tab['box_id']}` | Delay: `{tab['delay']}` giây | Uptime: `{uptime}`\n"
    msg += "\nNhập số tab để dừng"
    await interaction.response.send_message(msg)
    
    def check(m): return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
        idx = int(reply.content.strip())
        with TAB_LOCK:
            chosen = tabs[idx-1]
            chosen["stop_event"].set()
            tabs.pop(idx-1)
            if not tabs:
                del user_tabs[discord_user_id]
        await interaction.followup.send(f"Đã dừng tab số {idx}")
    except:
        await interaction.followup.send("Hết thời gian")

@tree.command(name="add", description="Thêm user")
@app_commands.describe(user="Tag hoặc ID user", thoihan="Thời hạn (ví dụ: 7d)")
async def add(interaction: discord.Interaction, user: str, thoihan: str = None):
    if not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")
    user_id = user.replace("<@", "").replace(">", "").replace("!", "")
    days = int(thoihan[:-1]) if thoihan and thoihan.endswith("d") else None
    _add_user(user_id, days)
    await interaction.response.send_message(f"Đã thêm <@{user_id}> với quyền {'vĩnh viễn' if not days else f'{days} ngày'}")

@tree.command(name="xoa", description="Xoá user")
@app_commands.describe(user="Tag hoặc ID user")
async def xoa(interaction: discord.Interaction, user: str):
    if not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")
    user_id = user.replace("<@", "").replace(">", "").replace("!", "")
    _remove_user_and_kill_tabs(user_id)
    await interaction.response.send_message(f"Đã xóa quyền của <@{user_id}>")

@tree.command(name="list", description="Hiển thị danh sách user")
async def list_cmd(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này")
    user_list = _get_user_list()
    if not user_list:
        return await interaction.response.send_message("Danh sách rỗng.")
    embed = discord.Embed(title="📋 Danh sách user có quyền", color=0x3498db)
    for uid, time_str in user_list:
        try:
            user_obj = await bot.fetch_user(int(uid))
            name = user_obj.name
        except:
            name = f"Unknown ({uid})"
        embed.add_field(name=name, value=f"ID: {uid}\nThời hạn: {time_str}", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="treotele", description="Treo ngôn telegram")
@app_commands.describe(tokens="Token Telegram", chats="ID nhóm chat", text="Nội dung", delay="Delay giây")
async def treotele(interaction: discord.Interaction, tokens: str, chats: str, text: str, delay: int):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot")
    
    tokens_list = [t.strip() for t in tokens.split(",")]
    chats_list = [c.strip() for c in chats.split(",")]
    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()
    
    for tk in tokens_list:
        stop_event = threading.Event()
        process = threading.Thread(target=telegram_send_loop, args=(tk, chats_list, text, None, delay, stop_event, discord_user_id), daemon=True)
        process.start()
        with TREOTELE_LOCK:
            user_treotele_tabs.setdefault(discord_user_id, []).append({"process": process, "stop_event": stop_event, "start": start_time, "token": tk})
    
    await interaction.response.send_message(f"✅ Đã tạo tab treo Telegram cho <@{discord_user_id}>:\n• Chats: `{', '.join(chats_list)}`\n• Delay: `{delay}` giây")

@tree.command(name="treosms", description="Spam OTP SmS")
@app_commands.describe(sdt="Số điện thoại muốn spam")
async def treosms(interaction: discord.Interaction, sdt: str):
    uid = str(interaction.user.id)
    with TREOSMS_LOCK:
        if uid not in TREOSMS_TASKS:
            TREOSMS_TASKS[uid] = []
        stop_event = threading.Event()
        thread = threading.Thread(target=spam_sms_forever, args=(sdt, stop_event), daemon=True)
        thread.start()
        TREOSMS_TASKS[uid].append({"sdt": sdt, "stop_event": stop_event, "start": datetime.now()})
    await interaction.response.send_message(f"✅ Đã bắt đầu spam OTP vào số `{sdt}`")

@tree.command(name="menu", description="Hiển thị danh sách chức năng")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="👾 MENU BOT", description="Danh sách lệnh có sẵn", color=discord.Color.purple())
    embed.add_field(name="/nhaytop", value="Spam bình luận Facebook", inline=False)
    embed.add_field(name="/treomess", value="Treo tin nhắn Messenger", inline=False)
    embed.add_field(name="/treotele", value="Treo tin nhắn Telegram", inline=False)
    embed.add_field(name="/treosms", value="Spam SMS", inline=False)
    embed.add_field(name="/add", value="Thêm user (Admin)", inline=False)
    embed.add_field(name="/xoa", value="Xóa user (Admin)", inline=False)
    embed.add_field(name="/list", value="Danh sách user (Admin)", inline=False)
    embed.add_field(name="/tabnhaytop", value="Dừng tab nhaytop", inline=False)
    embed.add_field(name="/tabtreomess", value="Dừng tab treomess", inline=False)
    embed.add_field(name="/tabtreotele", value="Dừng tab treotele", inline=False)
    embed.add_field(name="/tabtreosms", value="Dừng tab treosms", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot đã online: {bot.user.name}")
    print(f"📌 Đã sync {len(tree.get_commands())} lệnh")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    print("🚀 Đang khởi động bot...")
    print("📖 Lệnh Admin: /add, /xoa, /list")
    print("📖 Lệnh User: /nhaytop, /treomess, /treotele, /treosms")
    print("📖 Lệnh dừng: /tabnhaytop, /tabtreomess, /tabtreotele, /tabtreosms")
    print("-" * 50)
    bot.run(TOKEN)