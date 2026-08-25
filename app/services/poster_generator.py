# coding: utf-8
import os
import json
import html
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>VoteVictory Poster</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=Noto+Sans+Devanagari:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-font-smoothing: antialiased; }
  body { width: 1080px; height: 1350px; overflow: hidden; background: #ffffff; font-family: 'Outfit', 'Noto Sans Devanagari', sans-serif; }
  #poster-root { position: relative; width: 1080px; height: 1350px; background: #ffffff; overflow: hidden; }
  .top-strip { position: absolute; top: 0; left: 0; width: 1080px; height: 16px; background: linear-gradient(90deg, #FF9933 0%, #FF9933 33.3%, #FFFFFF 33.3%, #FFFFFF 66.6%, #138808 66.6%, #138808 100%); }
  .top-tagline { position: absolute; top: 28px; left: 60px; width: 960px; height: 48px; background: #FEF3C7; border: 1.5px solid #F59E0B; border-radius: 24px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 800; color: #92400E; letter-spacing: 0.5px; }
  .appeal-banner { position: absolute; top: 92px; left: 60px; width: 960px; height: 70px; background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 18px; display: flex; align-items: center; justify-content: space-between; padding: 0 28px; color: #ffffff; box-shadow: 0 6px 16px rgba(15, 23, 42, 0.15); }
  .appeal-banner .tag-left { font-size: 16px; font-weight: 800; color: #FBBF24; text-transform: uppercase; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }
  .appeal-banner .appeal-text { font-size: 22px; font-weight: 700; color: #F8FAFC; }
  .cand-greeting { position: absolute; top: 190px; left: 60px; width: 490px; height: 35px; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700; color: #64748B; letter-spacing: 1px; text-transform: uppercase; }
  .cand-name-box { position: absolute; top: 228px; left: 60px; width: 490px; height: 162px; display: flex; align-items: center; justify-content: center; text-align: center; padding: 6px 12px; overflow: hidden; }
  .cand-name-text { font-weight: 900; color: #D97706; line-height: 1.15; word-break: break-word; text-shadow: 0 2px 4px rgba(217, 119, 6, 0.12); }
  .position-pill { position: absolute; top: 405px; left: 60px; width: 490px; height: 75px; background: linear-gradient(135deg, #047857 0%, #065F46 100%); border-radius: 18px; display: flex; align-items: center; justify-content: center; text-align: center; padding: 0 16px; box-shadow: 0 4px 12px rgba(4, 120, 87, 0.25); overflow: hidden; }
  .position-text { font-weight: 800; color: #FFFFFF; line-height: 1.2; word-break: break-word; }
  .ward-badge { position: absolute; top: 495px; left: 60px; width: 235px; height: 105px; background: #F8FAFC; border: 2.5px solid #CBD5E1; border-radius: 18px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 6px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); }
  .badge-label { font-size: 13px; font-weight: 800; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
  .badge-val { font-size: 34px; font-weight: 900; color: #0F172A; line-height: 1; }
  .ballot-badge { position: absolute; top: 495px; left: 315px; width: 235px; height: 105px; background: #FEF3C7; border: 2.5px solid #F59E0B; border-radius: 18px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 6px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.12); }
  .ballot-badge .badge-label { color: #B45309; }
  .ballot-badge .badge-val { color: #92400E; }
  .symbol-box { position: absolute; top: 615px; left: 60px; width: 490px; height: 145px; background: #FFFFFF; border: 3px solid #F59E0B; border-radius: 20px; display: flex; align-items: center; padding: 10px 18px; gap: 16px; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.15); }
  .symbol-icon-wrap { width: 120px; height: 120px; background: #FEF3C7; border: 2px solid #FDE68A; border-radius: 16px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; overflow: hidden; }
  .symbol-icon-img { width: 100%; height: 100%; object-fit: contain; padding: 6px; }
  .symbol-icon-emoji { font-size: 72px; line-height: 1; }
  .symbol-meta { display: flex; flex-direction: column; justify-content: center; flex: 1; overflow: hidden; }
  .symbol-label-tag { font-size: 14px; font-weight: 800; color: #B45309; text-transform: uppercase; letter-spacing: 0.5px; }
  .symbol-name-text { font-size: 28px; font-weight: 900; color: #0F172A; margin-top: 2px; word-break: break-word; }
  .photo-frame { position: absolute; top: 190px; left: 580px; width: 440px; height: 570px; border-radius: 28px; border: 6px solid #F59E0B; background: #E2E8F0; overflow: hidden; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15); display: flex; align-items: center; justify-content: center; }
  .photo-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .photo-fallback { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; background: linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%); color: #94A3B8; }
  .photo-fallback-initial { font-size: 160px; font-weight: 900; color: #CBD5E1; line-height: 1; }
  .photo-fallback-tag { font-size: 20px; font-weight: 800; color: #94A3B8; margin-top: 12px; text-transform: uppercase; letter-spacing: 1px; }
  .slogan-box { position: absolute; top: 785px; left: 60px; width: 960px; height: 160px; background: #FFFBEB; border: 2px solid #FDE68A; border-left: 8px solid #D97706; border-radius: 20px; padding: 16px 28px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 4px 14px rgba(217, 119, 6, 0.08); overflow: hidden; }
  .slogan-title { font-size: 14px; font-weight: 800; color: #B45309; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
  .slogan-text { font-weight: 700; color: #1E293B; line-height: 1.35; word-break: break-word; font-style: italic; }
  .pillars-row { position: absolute; top: 965px; left: 60px; width: 960px; height: 215px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
  .pillar-card { background: #F8FAFC; border: 2px solid #E2E8F0; border-radius: 20px; padding: 20px 18px; display: flex; flex-direction: column; align-items: center; text-align: center; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); }
  .pillar-icon { font-size: 40px; margin-bottom: 8px; line-height: 1; }
  .pillar-title { font-size: 20px; font-weight: 800; color: #0F172A; margin-bottom: 4px; }
  .pillar-desc { font-size: 14px; font-weight: 600; color: #64748B; line-height: 1.3; }
  .footer-bar { position: absolute; top: 1205px; left: 60px; width: 960px; height: 115px; background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius: 24px; display: flex; align-items: center; justify-content: space-between; padding: 0 28px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2); }
  .footer-appeal { display: flex; flex-direction: column; justify-content: center; max-width: 600px; }
  .footer-appeal-main { font-size: 24px; font-weight: 900; color: #F8FAFC; letter-spacing: 0.5px; }
  .footer-appeal-sub { font-size: 15px; font-weight: 600; color: #94A3B8; margin-top: 2px; }
  .footer-contact { background: #D97706; border-radius: 16px; padding: 12px 24px; display: flex; align-items: center; gap: 10px; color: #FFFFFF; font-size: 22px; font-weight: 800; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.35); flex-shrink: 0; }
</style>
</head>
<body>
<div id="poster-root">
  <div class="top-strip"></div>
  <div class="top-tagline"><span>॥ ग्राम पंचायत आम चुनाव 2026 • निष्पक्ष, ईमानदार एवं कर्मठ नेतृत्व ॥</span></div>
  <div class="appeal-banner">
    <div class="tag-left"><span>★</span><span>Vote For Victory</span></div>
    <div class="appeal-text">सर्व समाज के प्रिय एवं विकासशील प्रत्याशी को भारी मतों से विजयी बनाएं</div>
  </div>
  <div class="cand-greeting">॥ आपका अपना प्रत्याशी ॥</div>
  <div class="cand-name-box"><span id="cand-name-text" class="cand-name-text">__CANDIDATE_NAME__</span></div>
  <div class="position-pill"><span id="position-text" class="position-text">__POSITION__</span></div>
  <div class="ward-badge"><span class="badge-label">वार्ड नंबर / WARD</span><span class="badge-val">__WARD_NO__</span></div>
  <div class="ballot-badge"><span class="badge-label">क्रमांक / BALLOT</span><span class="badge-val">__BALLOT_NO__</span></div>
  <div class="symbol-box">
    <div class="symbol-icon-wrap">__SYMBOL_CONTENT__</div>
    <div class="symbol-meta">
      <span class="symbol-label-tag">चुनाव चिह्न / ELECTION SYMBOL</span>
      <span class="symbol-name-text">__SYMBOL_NAME__</span>
    </div>
  </div>
  <div class="photo-frame">__PHOTO_CONTENT__</div>
  <div class="slogan-box">
    <div class="slogan-title"><span>📌</span><span>संकल्प एवं संदेश / Campaign Promise</span></div>
    <div id="slogan-text" class="slogan-text">"__SLOGAN__"</div>
  </div>
  <div class="pillars-row">
    <div class="pillar-card"><div class="pillar-icon">🤝</div><div class="pillar-title">ईमानदार नेतृत्व</div><div class="pillar-desc">हर वर्ग का सम्मान, सबकी बात, सबका साथ और निष्पक्ष सेवा</div></div>
    <div class="pillar-card"><div class="pillar-icon">⚡</div><div class="pillar-title">तेज विकास</div><div class="pillar-desc">पक्की सड़कें, शुद्ध पेयजल, 24 घंटे बिजली एवं स्वच्छता</div></div>
    <div class="pillar-card"><div class="pillar-icon">🗳️</div><div class="pillar-title">आपका एक वोट</div><div class="pillar-desc">ग्राम पंचायत के समग्र एवं उज्ज्वल भविष्य के लिए समर्पित</div></div>
  </div>
  <div class="footer-bar">
    <div class="footer-appeal"><div class="footer-appeal-main">चुनाव निशान के सामने वाला बटन दबाकर भारी मतों से विजयी बनाएं!</div><div class="footer-appeal-sub">निवेदक: समस्त ग्रामवासी एवं चुनाव प्रचार समिति</div></div>
    __CONTACT_CONTENT__
  </div>
</div>
<script>
function fitText(elId, maxFontSize, minFontSize, maxW, maxH) {
  var el = document.getElementById(elId);
  if (!el) return;
  var currentSize = maxFontSize;
  el.style.fontSize = currentSize + 'px';
  while (currentSize > minFontSize && (el.offsetWidth > maxW || el.offsetHeight > maxH || el.scrollWidth > maxW || el.scrollHeight > maxH)) {
    currentSize -= 1;
    el.style.fontSize = currentSize + 'px';
  }
}
window.addEventListener('DOMContentLoaded', function() {
  fitText('cand-name-text', 54, 20, 466, 148);
  fitText('position-text', 34, 18, 458, 62);
  fitText('slogan-text', 30, 16, 900, 95);
});
</script>
</body>
</html>"""

def build_poster_html(data: dict) -> str:
    name = (data.get("candidate_name") or "").strip() or "उम्मीदवार का नाम"
    position = (data.get("position") or "").strip() or "सरपंच प्रत्याशी"
    ward_no = (data.get("ward_no") or "").strip()
    ballot_no = (data.get("ballot_no") or "").strip()
    slogan = (data.get("slogan") or "").strip() or "गांव का समग्र विकास, हर घर विश्वास और खुशहाली!"
    contact = (data.get("contact") or "").strip()
    photo_url = (data.get("photo_url") or "").strip()
    symbol_url = (data.get("symbol_url") or "").strip()
    symbol_name = (data.get("symbol_name") or "").strip() or "चुनाव चिह्न"
    initial = (name[0] if name else "उ").upper()

    if symbol_url:
        symbol_content = f'<img src="{html.escape(symbol_url)}" class="symbol-icon-img" alt="Symbol" />'
    else:
        symbol_content = '<span class="symbol-icon-emoji">🚜</span>'

    if photo_url:
        photo_content = f'<img src="{html.escape(photo_url)}" class="photo-img" alt="Candidate Photo" />'
    else:
        photo_content = f'<div class="photo-fallback"><div class="photo-fallback-initial">{html.escape(initial)}</div><div class="photo-fallback-tag">प्रत्याशी फोटो</div></div>'

    if contact:
        contact_content = f'<div class="footer-contact"><span>📞</span><span>{html.escape(contact)}</span></div>'
    else:
        contact_content = ''

    res = HTML_TEMPLATE
    res = res.replace("__CANDIDATE_NAME__", html.escape(name))
    res = res.replace("__POSITION__", html.escape(position))
    res = res.replace("__WARD_NO__", html.escape(ward_no if ward_no else "—"))
    res = res.replace("__BALLOT_NO__", html.escape(ballot_no if ballot_no else "—"))
    res = res.replace("__SYMBOL_CONTENT__", symbol_content)
    res = res.replace("__SYMBOL_NAME__", html.escape(symbol_name))
    res = res.replace("__PHOTO_CONTENT__", photo_content)
    res = res.replace("__SLOGAN__", html.escape(slogan))
    res = res.replace("__CONTACT_CONTENT__", contact_content)
    return res

def generate_poster_image(data: dict, output_path: str, p_instance=None) -> str:
    html_src = build_poster_html(data)
    
    def run_on_playwright(p):
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.set_content(html_src, wait_until="domcontentloaded")
        page.wait_for_timeout(400)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=output_path, type="png")
        browser.close()
        
    if p_instance:
        run_on_playwright(p_instance)
    else:
        with sync_playwright() as p:
            run_on_playwright(p)
    return output_path
