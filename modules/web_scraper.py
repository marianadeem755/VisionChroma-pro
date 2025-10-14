import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def fetch_website_content(url, timeout=12):
    headers = {
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116 Safari/537.36",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer":"https://www.google.com"
    }
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429,500,502,503,504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    try:
        r = session.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text
    except Exception as e:
        try:
            stripped = re.sub(r'^https?://','',url)
            proxy = f"https://r.jina.ai/http://{stripped}"
            pr = session.get(proxy, headers=headers, timeout=timeout)
            pr.raise_for_status()
            return pr.text
        except Exception:
            print("❌ Fetch failed:", e)
            return None

def extract_website_data(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    nodes = soup.find_all(['p','li','h1','h2','h3','span','a'])
    text = " ".join([n.get_text(" ",strip=True) for n in nodes])
    text = re.sub(r'\s+',' ', text).strip()
    inline_styles = [t.get('style') for t in soup.find_all(style=True) if t.get('style')]
    combined_css = "\n".join(inline_styles)
    css_links = [urljoin(base_url, l.get('href')) for l in soup.find_all('link', rel='stylesheet') if l.get('href')]
    for css in css_links[:5]:
        try:
            r = requests.get(css, timeout=6)
            if r.status_code==200:
                combined_css += "\n" + r.text
        except:
            pass
    color_matches = re.findall(r'(?:color|background(?:-color)?)\s*:\s*([^;}{]+);?', combined_css, flags=re.IGNORECASE)
    font_matches = re.findall(r'font[- ]?family\s*:\s*([^;}{]+);?', combined_css, flags=re.IGNORECASE)
    colors = sorted(list({c.strip() for c in color_matches if c.strip() and len(c.strip())<40}))
    fonts = sorted(list({f.strip().strip('"').strip("'") for f in font_matches if f.strip()}))
    df_colors = pd.DataFrame(colors, columns=['Color Values']) if colors else pd.DataFrame(columns=['Color Values'])
    df_fonts = pd.DataFrame(fonts, columns=['Font Values']) if fonts else pd.DataFrame(columns=['Font Values'])
    images = [urljoin(base_url, img.get('src')) for img in soup.find_all('img') if img.get('src')]
    buttons = [b.get_text(" ",strip=True) for b in soup.find_all(['button','a']) if b.get_text(strip=True)]
    return {"text": text, "colors": df_colors, "fonts": df_fonts, "images": images, "buttons": buttons}
