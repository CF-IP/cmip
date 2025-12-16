import requests
import base64
import re
import time
import os
from pyvirtualdisplay import Display

# 引入新工具库
try:
    from DrissionPage import ChromiumPage, ChromiumOptions
except:
    pass

try:
    import undetected_chromedriver as uc
except:
    pass

try:
    from playwright.sync_api import sync_playwright
except:
    pass

# ================= 工具函数 =================

def is_valid_ip(ip):
    if not ip or len(ip) < 7:
        return False
    if '0.00%' in ip or '正在' in ip or '获取' in ip:
        return False
    # IPv4
    if re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return True
    # IPv6
    if ':' in ip and len(ip) > 5:
        return True
    return False

def fetch_content_requests(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.text
    except:
        return ""

# ================= 强力测试模式 =================

def run_drission_mode(url, mode_name, use_xvfb=True):
    results = []
    debug_info = "No Run"
    display = None
    page = None
    
    try:
        if use_xvfb:
            display = Display(visible=0, size=(1920, 1080))
            display.start()
        
        co = ChromiumOptions()
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        if not use_xvfb:
            co.headless() 
            
        page = ChromiumPage(co)
        page.get(url)
        
        # 等待真实数据加载 (等待15秒)
        time.sleep(15)
        
        debug_info = page.title
        
        # 获取表格
        rows = page.eles('tag:tr')
        for row in rows:
            cols = row.eles('tag:td')
            if len(cols) >= 3:
                line_type = cols[1].text.strip()
                ip = cols[2].text.strip()
                if is_valid_ip(ip):
                    results.append((line_type, ip))
                    
    except Exception as e:
        debug_info = f"Error: {str(e)}"
    finally:
        try:
            if page: page.quit()
        except: pass
        if display: display.stop()
        
    return results, debug_info

def run_undetected_mode(url, mode_name):
    results = []
    debug_info = "No Run"
    display = None
    driver = None
    
    try:
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = uc.Chrome(options=options, version_main=114) # 尝试指定版本或自动
        driver.get(url)
        time.sleep(15)
        
        debug_info = driver.title
        
        from selenium.webdriver.common.by import By
        rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                line_type = cols[1].text.strip()
                ip = cols[2].text.strip()
                if is_valid_ip(ip):
                    results.append((line_type, ip))
    except Exception as e:
        debug_info = f"Error: {str(e)}"
    finally:
        try:
            if driver: driver.quit()
        except: pass
        if display: display.stop()
        
    return results, debug_info

def run_playwright_mode(url, browser_type_name):
    results = []
    debug_info = "No Run"
    
    try:
        with sync_playwright() as p:
            if browser_type_name == 'chromium':
                browser = p.chromium.launch(headless=True)
            elif browser_type_name == 'firefox':
                browser = p.firefox.launch(headless=True)
            elif browser_type_name == 'webkit':
                browser = p.webkit.launch(headless=True)
            else:
                return [], "Unknown Browser"
                
            page = browser.new_page()
            page.goto(url)
            page.wait_for_timeout(15000) # 等待15秒
            
            debug_info = page.title()
            
            rows = page.locator("tr").all()
            for row in rows:
                cols = row.locator("td").all()
                if len(cols) >= 3:
                    line_type = cols[1].inner_text().strip()
                    ip = cols[2].inner_text().strip()
                    if is_valid_ip(ip):
                        results.append((line_type, ip))
            browser.close()
    except Exception as e:
        debug_info = f"Error: {str(e)}"
        
    return results, debug_info

def fetch_all_test_modes(url):
    all_found = []
    report_logs = []
    
    # 1. DrissionPage 模式 (目前最强)
    print("Running DrissionPage...")
    data, info = run_drission_mode(url, "DP_Xvfb", use_xvfb=True)
    report_logs.append(f"Mode: DrissionPage_Xvfb | Title: {info} | Found: {len(data)}")
    if data:
        for lt, ip in data: all_found.append(f"{ip}#DP_Xvfb_{lt}")

    # 2. Undetected Chromedriver (UC)
    # print("Running Undetected Chromedriver...")
    # data, info = run_undetected_mode(url, "UC_Default")
    # report_logs.append(f"Mode: UC_Default | Title: {info} | Found: {len(data)}")
    # if data:
    #    for lt, ip in data: all_found.append(f"{ip}#UC_{lt}")
    # UC 在 Github Actions 环境极易报错，暂时注释，先跑 Playwright

    # 3. Playwright Firefox (火狐内核，指纹不同)
    print("Running Playwright Firefox...")
    data, info = run_playwright_mode(url, "firefox")
    report_logs.append(f"Mode: PW_Firefox | Title: {info} | Found: {len(data)}")
    if data:
        for lt, ip in data: all_found.append(f"{ip}#PW_Firefox_{lt}")

    # 4. Playwright Webkit (Safari内核)
    print("Running Playwright Webkit...")
    data, info = run_playwright_mode(url, "webkit")
    report_logs.append(f"Mode: PW_Webkit | Title: {info} | Found: {len(data)}")
    if data:
        for lt, ip in data: all_found.append(f"{ip}#PW_Webkit_{lt}")
        
    return all_found, report_logs

# ================= 主程序 =================

def fetch_and_parse_lines(url):
    content = fetch_content_requests(url)
    if not content:
        return []
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    return lines

def get_real_sub_url(page_url):
    content = fetch_content_requests(page_url)
    if not content:
        return None
    urls = re.findall(r'https?://[^\s"\'<>]+', content)
    target_urls = [u for u in urls if '?uuid=' in u]
    if target_urls: return target_urls[0]
    if urls: return max(urls, key=len)
    return None

def parse_proxy_nodes(sub_url):
    content = fetch_content_requests(sub_url)
    if not content:
        return []
    try:
        missing_padding = len(content) % 4
        if missing_padding: content += '=' * (4 - missing_padding)
        decoded_data = base64.b64decode(content).decode('utf-8', errors='ignore')
    except:
        return []

    nodes = []
    for line in decoded_data.split('\n'):
        if line.startswith('vless://'):
            try:
                main_part = line.replace('vless://', '')
                if '#' in main_part: config_part, remark = main_part.split('#', 1)
                else: config_part, remark = main_part, ""
                remark = requests.utils.unquote(remark).strip()
                if '@' in config_part:
                    user_info, host_info = config_part.split('@', 1)
                    address_part = host_info.split('?')[0] if '?' in host_info else host_info
                    if ':' in address_part:
                        ip, port = address_part.split(':')[0], address_part.split(':')[1]
                        if port == '443' and len(remark) >= 2 and re.match(r'^[A-Za-z]{2}', remark) and is_valid_ip(ip):
                             nodes.append(f"{ip}#{remark[0:2].upper()}（反代IP）")
            except: continue
    return nodes

def main():
    url_ct = "https://cf.090227.xyz/ct?ips=6"
    url_cu = "https://cf.090227.xyz/cu"
    url_cm = "https://cf.090227.xyz/cmcc?ips=8"
    url_other = "https://cf.090227.xyz/ip.164746.xyz"
    url_mixed = "https://cf.090227.xyz/CloudFlareYes"
    url_selenium_target = "https://api.uouin.com/cloudflare.html"
    url_sub_page = "https://getsub.classelivre.eu.org/sub"

    final_list = []
    seen_ips = set()
    
    # 1. 常规源
    def process_url(url, type_name_prefix):
        lines = fetch_and_parse_lines(url)
        count = 0
        for line in lines:
            if '#' in line: ip = line.split('#')[0].strip()
            else: ip = line.strip()
            if is_valid_ip(ip) and ip not in seen_ips:
                seen_ips.add(ip)
                count += 1
                final_list.append(f"{ip}#{type_name_prefix}{count}")
    
    process_url(url_ct, "电信")
    process_url(url_cu, "联通")
    process_url(url_cm, "移动")
    process_url(url_other, "其他")
    
    lines_mixed = fetch_and_parse_lines(url_mixed)
    c_m_ct, c_m_cu, c_m_cm, c_m_ot = 100, 100, 100, 100
    for line in lines_mixed:
        if '#' in line:
            parts = line.split('#')
            ip = parts[0].strip()
            remark = parts[1].strip().upper()
            if is_valid_ip(ip) and ip not in seen_ips:
                seen_ips.add(ip)
                if remark.startswith('CM'): 
                    final_list.append(f"{ip}#移动{c_m_cm}")
                    c_m_cm += 1
                elif remark.startswith('CU'): 
                    final_list.append(f"{ip}#联通{c_m_cu}")
                    c_m_cu += 1
                elif remark.startswith('CT'): 
                    final_list.append(f"{ip}#电信{c_m_ct}")
                    c_m_ct += 1
                else: 
                    final_list.append(f"{ip}#其他{c_m_ot}")
                    c_m_ot += 1

    # 2. 强力测试模式 (DrissionPage / Playwright)
    print("Start Advanced Scraping...")
    test_results, logs = fetch_all_test_modes(url_selenium_target)
    final_list.extend(test_results)

    # 3. 反代源
    real_sub_url = get_real_sub_url(url_sub_page)
    if real_sub_url:
        proxy_nodes = parse_proxy_nodes(real_sub_url)
        final_list.extend(proxy_nodes)

    # 4. 输出
    with open('cmip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_list))
    
    with open('ip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_list))
        
    def save_keyword(keyword, filename):
        lines = [l for l in final_list if keyword in l]
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
    save_keyword("电信", "ct.txt")
    save_keyword("联通", "cu.txt")
    save_keyword("移动", "cm.txt")
    save_keyword("多线", "多线.txt")
    save_keyword("IPV6", "ipv6.txt")
    save_keyword("反代IP", "反代.txt")
    
    # 写入详细的调试日志
    with open('测试报告.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(logs))

if __name__ == "__main__":
    main()
