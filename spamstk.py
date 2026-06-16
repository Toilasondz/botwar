import os
import sys
import re
import time
import json
import random
import threading
import asyncio
import requests
import smtplib
import ssl
import uuid
from io import BytesIO
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from Crypto.Cipher import AES
import base64
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

# ==================== API CONFIGURATION ====================
API_BASE_URL = "http://localhost:5000/api"

class APIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def post(self, endpoint: str, data: Dict = None) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.post(url, json=data, timeout=30)
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get(self, endpoint: str, params: Dict = None) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

api = APIClient()

# ==================== DATA MANAGER ====================
class DataManager:
    @staticmethod
    def save_messages(user_id: str, messages: List[str], filename: str) -> bool:
        result = api.post("messages/save", {
            "user_id": user_id, "filename": filename, "messages": messages
        })
        return result.get("success", False)
    
    @staticmethod
    def load_messages(user_id: str, filename: str) -> List[str]:
        result = api.get("messages/load", {"user_id": user_id, "filename": filename})
        if result.get("success"):
            return result.get("messages", [])
        return []
    
    @staticmethod
    def list_messages(user_id: str) -> List[str]:
        result = api.get("messages/list", {"user_id": user_id})
        if result.get("success"):
            return result.get("files", [])
        return []
    
    @staticmethod
    def save_cookie(user_id: str, cookie_data: Dict, name: str) -> bool:
        result = api.post("cookies/save", {
            "user_id": user_id, "name": name, "cookie_data": cookie_data
        })
        return result.get("success", False)
    
    @staticmethod
    def load_cookie(user_id: str, name: str) -> Dict:
        result = api.get("cookies/load", {"user_id": user_id, "name": name})
        if result.get("success"):
            return result.get("cookie_data", {})
        return {}
    
    @staticmethod
    def list_cookies(user_id: str) -> List[str]:
        result = api.get("cookies/list", {"user_id": user_id})
        if result.get("success"):
            return result.get("cookies", [])
        return []
    
    @staticmethod
    def save_spam_list(user_id: str, content: List[str], list_type: str) -> bool:
        result = api.post("spam_lists/save", {
            "user_id": user_id, "type": list_type, "content": content
        })
        return result.get("success", False)
    
    @staticmethod
    def load_spam_list(user_id: str, list_type: str) -> List[str]:
        result = api.get("spam_lists/load", {"user_id": user_id, "type": list_type})
        if result.get("success"):
            return result.get("content", [])
        return []
    
    @staticmethod
    def delete_spam_item(user_id: str, list_type: str, index: int) -> bool:
        result = api.post("spam_lists/delete", {
            "user_id": user_id, "type": list_type, "index": index
        })
        return result.get("success", False)
    
    @staticmethod
    def save_session(user_id: str, session_data: Dict) -> bool:
        result = api.post("sessions/save", {
            "user_id": user_id, "session_data": session_data
        })
        return result.get("success", False)
    
    @staticmethod
    def load_session(user_id: str) -> Dict:
        result = api.get("sessions/load", {"user_id": user_id})
        if result.get("success"):
            return result.get("session_data", {})
        return {}

# ==================== UTILITIES ====================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_uptime(start_time: datetime) -> str:
    elapsed = (datetime.now() - start_time).total_seconds()
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def get_guid():
    return str(uuid.uuid4())

def normalize_cookie(cookie: str, domain: str = 'www.facebook.com') -> str:
    headers = {'Cookie': cookie, 'User-Agent': 'Mozilla/5.0'}
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

def parse_cookie_string(cookie_str: str) -> Dict:
    try:
        cookie_str = cookie_str.strip()
        if cookie_str.startswith("{") and cookie_str.endswith("}"):
            return json.loads(cookie_str)
        data = {}
        for part in cookie_str.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                data[k.strip()] = v.strip()
        if "session_key" not in data and "zpw_sek" in data:
            data["session_key"] = data["zpw_sek"]
        return data if "session_key" in data else None
    except:
        return None

def get_uid_fbdtsg(ck: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    try:
        headers = {'Accept': 'text/html', 'Cookie': ck, 'User-Agent': 'Mozilla/5.0'}
        response = requests.get('https://www.facebook.com/', headers=headers, timeout=15)
        html = response.text
        user_id = re.search(r'"USER_ID":"(\d+)"', html)
        fb_dtsg = re.search(r'"f":"([^"]+)"', html)
        jazoest = re.search(r'jazoest=(\d+)', html)
        rev = re.search(r'"server_revision":(\d+),"client_revision":(\d+)', html)
        a = re.search(r'__a=(\d+)', html)
        if not all([user_id, fb_dtsg, jazoest, rev]):
            return None, None, None, None, None, None
        return user_id.group(1), fb_dtsg.group(1), rev.group(1), "1b", (a.group(1) if a else "1"), jazoest.group(1)
    except:
        return None, None, None, None, None, None

def extract_facebook_post_id(link: str) -> Optional[str]:
    match = re.search(r"fbid=(\d+)", link)
    if not match:
        match = re.search(r"/posts/(\d+)", link)
    if not match:
        match = re.search(r"/videos/(\d+)", link)
    if not match:
        match = re.search(r"/permalink/(\d+)", link)
    return match.group(1) if match else None

def get_thread_list(cookie: str) -> List[Dict]:
    try:
        headers = {'Cookie': cookie, 'User-Agent': 'Mozilla/5.0'}
        response = requests.get('https://www.facebook.com/messages/t/', headers=headers, timeout=15)
        html = response.text
        threads = re.findall(r'thread_fbid":"(\d+)","name":"([^"]+)"', html)
        return [{"thread_id": tid, "thread_name": name} for tid, name in threads]
    except:
        return []

# ==================== CORE CLASSES ====================
class Kem:
    def __init__(self, cookie: str):
        self.cookie = normalize_cookie(cookie)
        self.user_id = self._get_user_id()
        self.fb_dtsg = None
        self._init_params()
    
    def _get_user_id(self):
        try:
            match = re.search(r"c_user=(\d+)", self.cookie)
            if match:
                return match.group(1)
            raise Exception("Cookie không hợp lệ")
        except:
            raise Exception("Cookie không hợp lệ")
    
    def _init_params(self):
        headers = {'Cookie': self.cookie, 'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get('https://www.facebook.com', headers=headers, timeout=15)
            fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
            if not fb_dtsg_match:
                response = requests.get('https://mbasic.facebook.com', headers=headers, timeout=15)
                fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
            if fb_dtsg_match:
                self.fb_dtsg = fb_dtsg_match.group(1)
            else:
                raise Exception("Không thể lấy fb_dtsg")
        except Exception as e:
            raise Exception(f"Lỗi khởi tạo: {e}")
    
    def gui_tn(self, recipient_id: str, message: str, image_id: str = None) -> Dict:
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
        if image_id:
            data['sticker_id'] = image_id
            data['has_attachment'] = 'true'
        
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'python-http/0.27.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        try:
            response = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                return {'success': True}
            return {'success': False, 'error': f'Status: {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

class Mention:
    def __init__(self, thread_id: str, offset: int, length: int):
        self.thread_id = thread_id
        self.offset = offset
        self.length = length
    
    def to_send_data(self, i: int) -> Dict:
        return {
            f"profile_xmd[{i}][id]": self.thread_id,
            f"profile_xmd[{i}][offset]": self.offset,
            f"profile_xmd[{i}][length]": self.length,
            f"profile_xmd[{i}][type]": "p",
        }

class ThreadType(Enum):
    USER = 1
    GROUP = 2

class ZaloAPI:
    def __init__(self, imei: str, cookies: Dict):
        self.session = requests.Session()
        self.imei = imei
        self.secret_key = None
        self.uid = None
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://chat.zalo.me",
            "Referer": "https://chat.zalo.me/",
        })
        self.session.cookies.update(cookies)
        self._login()
    
    def _login(self):
        url = "https://wpa.chat.zalo.me/api/login/getLoginInfo"
        params = {"imei": self.imei, "type": 30, "client_version": 645, "ts": int(time.time() * 1000)}
        response = self.session.get(url, params=params, timeout=15)
        data = response.json()
        user_data = data.get("data")
        if not user_data:
            raise Exception("Login failed")
        self.uid = user_data.get("send2me_id")
        self.secret_key = user_data.get("zpw_enk")
        if not self.secret_key:
            raise Exception("Không lấy được secret_key")
    
    def fetch_groups(self) -> List[Dict]:
        url = "https://tt-group-wpa.chat.zalo.me/api/group/getlg/v4"
        params = {"zpw_ver": 645, "zpw_type": 30}
        response = self.session.get(url, params=params, timeout=15)
        data = response.json()
        decoded = self._zalo_decode(data.get("data", ""), self.secret_key)
        if not decoded:
            return []
        parsed = json.loads(decoded)
        grid_map = parsed.get("data", {}).get("gridVerMap", {})
        groups = []
        for group_id in sorted(grid_map.keys(), key=lambda x: int(x)):
            groups.append({"id": group_id, "name": grid_map[group_id].get("name", "Unknown")})
        return groups
    
    def fetch_friends(self) -> List[Dict]:
        url = "https://profile-wpa.chat.zalo.me/api/social/friend/getfriends"
        params = {"zpw_ver": 645, "zpw_type": 30}
        encoded = self._zalo_encode({"offset": 0, "count": 1000}, self.secret_key)
        response = self.session.post(url, params=params, data={"params": encoded}, timeout=15)
        result = response.json()
        decrypted = self._zalo_decode(result.get("data", ""), self.secret_key)
        if not decrypted:
            return []
        parsed = json.loads(decrypted)
        data_section = parsed.get("data", [])
        if isinstance(data_section, list):
            users = data_section
        else:
            users = data_section.get("users", [])
        return [{"id": u.get("userId"), "name": u.get("zaloName", "Unknown")} for u in users]
    
    def send_message(self, message: str, thread_id: str, thread_type: ThreadType) -> Dict:
        is_group = thread_type == ThreadType.GROUP
        url = "https://tt-group-wpa.chat.zalo.me/api/group/sendmsg" if is_group else "https://tt-chat2-wpa.chat.zalo.me/api/message/sms"
        payload = {
            "message": message,
            "clientId": str(int(time.time() * 1000)),
            "imei": self.imei
        }
        if is_group:
            payload["visibility"] = 0
            payload["grid"] = str(thread_id)
        else:
            payload["toid"] = str(thread_id)
        encoded = self._zalo_encode(payload, self.secret_key)
        response = self.session.post(url, params={"zpw_ver": 645, "zpw_type": 30}, data={"params": encoded}, timeout=30)
        return response.json()
    
    def set_typing(self, thread_id: str, thread_type: ThreadType):
        params = {"zpw_ver": 645, "zpw_type": 30}
        payload = {"imei": self.imei}
        if thread_type == ThreadType.USER:
            url = "https://tt-chat1-wpa.chat.zalo.me/api/message/typing"
            payload["toid"] = str(thread_id)
            payload["destType"] = 3
        else:
            url = "https://tt-group-wpa.chat.zalo.me/api/group/typing"
            payload["grid"] = str(thread_id)
        encoded = self._zalo_encode(payload, self.secret_key)
        self.session.post(url, params=params, data={"params": encoded}, timeout=10)
    
    def _zalo_encode(self, params: Dict, key: str) -> str:
        key_bytes = base64.b64decode(key)
        iv = bytes(16)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
        plaintext = json.dumps(params).encode()
        pad_len = AES.block_size - len(plaintext) % AES.block_size
        padded = plaintext + bytes([pad_len] * pad_len)
        return base64.b64encode(cipher.encrypt(padded)).decode()
    
    def _zalo_decode(self, encrypted_data: str, key: str) -> str:
        try:
            key_bytes = base64.b64decode(key)
            iv = bytes(16)
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(base64.b64decode(encrypted_data))
            pad_len = decrypted[-1]
            return decrypted[:-pad_len].decode('utf-8', errors='ignore')
        except:
            return ""

class SpamTool(ZaloAPI):
    def __init__(self, name: str, imei: str, cookies: Dict, thread_ids: List[str], thread_type: ThreadType, use_typing: bool = False):
        super().__init__(imei, cookies)
        self.name = name
        self.thread_ids = thread_ids
        self.thread_type = thread_type
        self.use_typing = use_typing
        self.running = False
    
    def send_spam(self, messages: List[str], delay: float, stop_event: threading.Event):
        self.running = True
        msg_index = 0
        
        while self.running and not stop_event.is_set():
            for thread_id in self.thread_ids:
                if not self.running or stop_event.is_set():
                    break
                
                message = messages[msg_index % len(messages)]
                
                try:
                    if self.use_typing:
                        self.set_typing(thread_id, self.thread_type)
                        time.sleep(1.5)
                    
                    result = self.send_message(message, thread_id, self.thread_type)
                    short_msg = (message[:50] + "...") if len(message) > 50 else message
                    print(f"[ZALO#{thread_id}] ✅ {short_msg}")
                except Exception as e:
                    print(f"[ZALO#{thread_id}] ❌ {e}")
                
                time.sleep(delay / len(self.thread_ids))
            
            msg_index += 1
            time.sleep(delay)

# ==================== SPAM WORKERS ====================
class SpamManager:
    def __init__(self):
        self.tabs: Dict[int, Dict] = {}
        self.tab_counter = 0
        self.lock = threading.Lock()
    
    def create_tab(self, tab_type: str, target_func, **kwargs) -> int:
        with self.lock:
            self.tab_counter += 1
            tab_id = self.tab_counter
            stop_event = threading.Event()
            
            thread = threading.Thread(
                target=target_func,
                args=(stop_event,),
                kwargs=kwargs,
                daemon=True
            )
            
            self.tabs[tab_id] = {
                "id": tab_id,
                "type": tab_type,
                "stop_event": stop_event,
                "thread": thread,
                "start_time": datetime.now(),
                "kwargs": kwargs
            }
            
            thread.start()
            
            # Lưu lên API
            api.post("tabs/create", {
                "tab_id": str(tab_id),
                "tab_info": {
                    "type": tab_type,
                    "user_id": kwargs.get("user_id", "unknown"),
                    "start_time": datetime.now().isoformat()
                }
            })
            
            return tab_id
    
    def stop_tab(self, tab