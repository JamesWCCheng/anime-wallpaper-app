import streamlit as st
import requests
from PIL import Image, ImageOps, ImageFilter
from io import BytesIO
import time

# --- 頁面設定 ---
st.set_page_config(page_title="AniList 官方圖庫", layout="wide")
st.title("⛩️ 動漫官方圖庫 (AniList 穩定版)")
st.markdown("使用最穩定的 AniList 核心。支援切換「不同季數/劇場版」的封面與橫幅。")

# --- Session State (用來記住現在看到第幾個結果) ---
if 'anime_index' not in st.session_state:
    st.session_state.anime_index = {} # 格式: {'咒術迴戰': 0}

# --- 內建翻譯字典 (你的好朋友) ---
ANIME_DICT = {
    "咒術迴戰": "Jujutsu Kaisen",
    "鬼滅之刃": "Demon Slayer",
    "進擊的巨人": "Attack on Titan",
    "鏈鋸人": "Chainsaw Man",
    "我推的孩子": "Oshi no Ko",
    "間諜家家酒": "Spy x Family",
    "SPY×FAMILY": "Spy x Family",
    "葬送的芙莉蓮": "Frieren",
    "排球少年": "Haikyuu",
    "航海王": "One Piece",
    "海賊王": "One Piece",
    "火影忍者": "Naruto",
    "七龍珠": "Dragon Ball",
    "死神": "Bleach",
    "獵人": "Hunter x Hunter",
    "一拳超人": "One Punch Man",
    "我的英雄學院": "My Hero Academia",
    "藍色監獄": "Blue Lock",
    "孤獨搖滾": "Bocchi the Rock",
    "刀劍神域": "Sword Art Online",
    "藥師少女": "The Apothecary Diaries"
}

# --- 1. AniList 核心 (一次抓 10 筆結果) ---
def search_anilist_media(query):
    # 翻譯
    search_term = query.strip()
    for cn, en in ANIME_DICT.items():
        if cn in search_term:
            search_term = en
            break
            
    url = 'https://graphql.anilist.co'
    # 這次我們抓 Page (多筆結果)，而不只是單筆
    query_body = '''
    query ($search: String) {
      Page(page: 1, perPage: 10) {
        media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
          id
          title {
            english
            romaji
            native
          }
          coverImage {
            extraLarge
          }
          bannerImage
        }
      }
    }
    '''
    try:
        resp = requests.post(url, json={'query': query_body, 'variables': {'search': search_term}}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', {}).get('Page', {}).get('media', [])
    except Exception as e:
        st.error(f"連線錯誤: {e}")
    return []

# --- 2. 圖片處理 (裁切與特效) ---
def process_mobile(img):
    return ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)

def process_desktop_blur(img):
    """電腦版磨砂特效"""
    target_w, target_h = 1920, 1080
    canvas = Image.new('RGB', (target_w, target_h), (0, 0, 0))
    
    # 背景
    bg = img.copy()
    ratio = target_w / bg.width
    bg_resize = bg.resize((int(bg.width * ratio), int(bg.height * ratio)), Image.Resampling.LANCZOS)
    bg_crop = ImageOps.fit(bg_resize, (target_w, target_h), centering=(0.5, 0.5))
    bg_blur = bg_crop.filter(ImageFilter.GaussianBlur(radius=30))
    bg_final = Image.eval(bg_blur, lambda x: x * 0.6) # 稍微調暗
    canvas.paste(bg_final, (0, 0))
    
    # 前景 (調整大小以適應高度)
    h_ratio = (target_h * 0.95) / img.height
    new_h = int(img.height * h_ratio)
    new_w = int(img.width * h_ratio)
    fg_resize = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    pos_x = (target_w - new_w) // 2
    pos_y = (target_h - new_h) // 2
    canvas.paste(fg_resize, (pos_x, pos_y))
    return canvas

def dl_btn(label, img, filename, key):
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.download_button(label, data=buf.getvalue(), file_name=filename, mime="image/png", key=key)

# --- 主介面 ---

default_input = "咒術迴戰, 鬼滅之刃, 我推的孩子"
anime_input = st.text_area("輸入動漫名稱 (逗號分隔)", value=default_input, height=70)

if st.button("🔍 搜尋動漫", type="primary"):
    # 重置 index
    st.session_state.anime_index = {}
    st.session_state.search_query = anime_input

# 顯示邏輯
if 'search_query' in st.session_state:
    queries = [x.strip() for x in st.session_state.search_query.split(',') if x.strip()]
    
    for q in queries:
        st.divider()
        
        # 1. 取得該動漫的搜尋列表
        results = search_anilist_media(q)
        
        if not results:
            st.warning(f"找不到關於「{q}」的資料")
            continue
            
        # 2. 決定現在要顯示第幾個結果
        if q not in st.session_state.anime_index:
            st.session_state.anime_index[q] = 0
        
        current_idx = st.session_state.anime_index[q] % len(results) # 循環顯示
        data = results[current_idx]
        
        # 3. 顯示標題與切換按鈕
        title = data['title']['english'] or data['title']['romaji']
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(f"🎬 {title}")
            st.caption(f"搜尋結果: {current_idx + 1} / {len(results)} (按右邊按鈕換下一部)")
        with c2:
            if st.button(f"🔄 切換下一張 ({q})", key=f"next_{q}"):
                st.session_state.anime_index[q] += 1
                st.rerun()
        
        # 4. 圖片展示區 (直式封面 + 橫式 Banner)
        col_cover, col_banner = st.columns([1, 2])
        
        # --- 直式封面 (Cover) ---
        with col_cover:
            st.write("**直式封面 (Portrait)**")
            cover_url = data['coverImage'].get('extraLarge')
            if cover_url:
                try:
                    r = requests.get(cover_url, timeout=5)
                    cover_img = Image.open(BytesIO(r.content))
                    st.image(cover_img, use_container_width=True)
                    
                    # 下載選項
                    with st.expander("📲 下載封面桌布"):
                        mob_img = process_mobile(cover_img)
                        dl_btn("📱 下載手機版 (9:16)", mob_img, f"{title}_mobile.png", f"m_{title}_{current_idx}")
                        
                        pc_blur = process_desktop_blur(cover_img)
                        dl_btn("💻 下載電腦版 (磨砂特效)", pc_blur, f"{title}_blur_pc.png", f"pc_{title}_{current_idx}")
                        
                        dl_btn("⬇️ 下載原圖", cover_img, f"{title}_cover.png", f"raw_{title}_{current_idx}")
                except:
                    st.error("封面圖載入失敗")
            else:
                st.info("無封面圖")

        # --- 橫式橫幅 (Banner) ---
        with col_banner:
            st.write("**橫式橫幅 (Banner)**")
            banner_url = data.get('bannerImage')
            if banner_url:
                try:
                    r2 = requests.get(banner_url, timeout=5)
                    banner_img = Image.open(BytesIO(r2.content))
                    st.image(banner_img, use_container_width=True)
                    
                    # 下載選項
                    with st.expander("💻 下載橫幅桌布"):
                        dl_btn("⬇️ 下載橫幅原圖", banner_img, f"{title}_banner.png", f"ban_{title}_{current_idx}")
                        
                        # 如果橫幅夠大，也可以切成手機版(選中間)
                        mob_banner = process_mobile(banner_img)
                        dl_btn("📱 下載橫幅裁切版 (手機)", mob_banner, f"{title}_ban_mob.png", f"ban_m_{title}_{current_idx}")
                except:
                    st.error("橫幅載入失敗")
            else:
                st.info("💡 此作品 AniList 未提供橫幅 (Banner)，請嘗試按「切換」找別季。")