import requests
import base64
import re
import time
import cloudscraper
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# ================= 工具函数 =================

def is_valid_ip(ip):
    # 简单的IP格式校验，过滤掉 "0.00%" 或文本
    if not ip or len(ip) < 7:
        return False
    if '0.00%' in ip:
        return False
    # IPv4
    if re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return True
    # IPv6 (简单判断)
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

# ================= 15种测试模式 =================

def get_selenium_driver(mode_config):
    options = Options()
    
    # 基础配置
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # 模式配置
    if mode_config.get('headless'):
        options.add_argument("--headless")
    
    if mode_config.get('incognito'):
        options.add_argument("--incognito")
        
    if mode_config.get('user_agent'):
        options.add_argument(f"user-agent={mode_config['user_agent']}")
        
    if mode_config.get('window_size'):
        options.add_argument(f"--window-size={mode_config['window_size']}")
        
    if mode_config.get('stealth'):
        # 移除自动化标记
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # CDP 进一步隐藏 (Stealth模式专用)
    if mode_config.get('stealth'):
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
    
    return driver

def run_test_mode(url, mode_name, config):
    print(f"Running Mode: {mode_name}")
    results = []
    driver = None
    display = None
    
    try:
        # 如果需要虚拟显示器 (非 Headless)
        if config.get('use_xvfb'):
            display = Display(visible=0, size=(1920, 1080))
            display.start()
            
        # 1. CloudScraper 特殊处理
        if mode_name == "模式02_CloudScraper":
            scraper = cloudscraper.create_scraper()
            text = scraper.get(url).text
            # 这里简单解析，因为 CloudScraper 返回的是 HTML 文本，需要正则提取
            # 假设网页结构不变，尝试正则提取
            # 注意：如果该网站完全依赖 JS 渲染表格，Cloudscraper 可能拿不到数据
            # 但作为一种模式，我们尝试一下
            # 这里的正则非常宽泛，仅作尝试
            return [] # Cloudscraper 不支持 JS 渲染，大概率对动态表格无效，但保留占位

        # 2. Selenium 处理
        driver = get_selenium_driver(config)
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        # 等待策略
        wait_time = config.get('wait_time', 10)
        time.sleep(wait_time)
        
        # 交互策略
        if config.get('scroll'):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
        # 提取数据
        rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                line_type = cols[1].text.strip()
                ip = cols[2].text.strip()
                if is_valid_ip(ip):
                    results.append((line_type, ip))
                    
    except Exception as e:
        print(f"Error in {mode_name}: {e}")
    finally:
        if driver:
            driver.quit()
        if display:
            display.stop()
            
    return results

def fetch_all_test_modes(url):
    all_found = []
    
    # === 定义 15 种模式配置 ===
    configs = [
        # --- 组1: 常规 Headless (容易被拦) ---
        ("模式03_Headless_Win10", {"headless": True, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "window_size": "1920,1080"}),
        ("模式04_Headless_Mac",   {"headless": True, "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "window_size": "1920,1080"}),
        
        # --- 组2: Headless + Stealth (隐藏自动化特征) ---
        ("模式05_Stealth_默认",   {"headless": True, "stealth": True, "window_size": "1920,1080"}),
        ("模式06_Stealth_Win10",  {"headless": True, "stealth": True, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "window_size": "1920,1080"}),
        ("模式07_Stealth_长等待", {"headless": True, "stealth": True, "wait_time": 20, "window_size": "1920,1080"}), # 等20秒
        
        # --- 组3: XVFB 虚拟显示器 (模拟真机，最强力) ---
        # 这一组完全不使用 --headless 参数，而是由服务器虚拟一个屏幕
        ("模式08_Xvfb_默认",      {"use_xvfb": True, "stealth": False, "window_size": "1920,1080"}),
        ("模式09_Xvfb_Stealth",   {"use_xvfb": True, "stealth": True, "window_size": "1920,1080"}),
        ("模式10_Xvfb_Win10",     {"use_xvfb": True, "stealth": True, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "window_size": "1920,1080"}),
        ("模式11_Xvfb_超大屏",    {"use_xvfb": True, "stealth": True, "window_size": "2560,1440"}),
        ("模式12_Xvfb_滚动加载",  {"use_xvfb": True, "stealth": True, "scroll": True, "wait_time": 15, "window_size": "1920,1080"}),
        
        # --- 组4: 移动端模拟 ---
        ("模式13_Stealth_iPhone", {"headless": True, "stealth": True, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", "window_size": "375,812"}),
        ("模式14_Xvfb_Android",   {"use_xvfb": True, "stealth": True, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36", "window_size": "412,915"}),
    ]

    # 依次运行
    for name, cfg in configs:
        data = run_test_mode(url, name, cfg)
        if data:
            print(f"Success: {name} found {len(data)} IPs")
            for line_type, ip in data:
                all_found.append(f"{ip}#{name}_{line_type}")
        else:
            print(f"Fail: {name}")

    return all_found

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

    # 容器
    final_list = []
    
    # 1. 常规源获取 (保持不变)
    seen_ips = set()
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
    
    # Mixed 源
    lines_mixed = fetch_and_parse_lines(url_mixed)
    count_m_ct, count_m_cu, count_m_cm, count_m_other = 100, 100, 100, 100
    for line in lines_mixed:
        if '#' in line:
            parts = line.split('#')
            ip = parts[0].strip()
            remark = parts[1].strip().upper()
            if is_valid_ip(ip) and ip not in seen_ips:
                seen_ips.add(ip)
                if remark.startswith('CM'): 
                    final_list.append(f"{ip}#移动{count_m_cm}")
                    count_m_cm += 1
                elif remark.startswith('CU'): 
                    final_list.append(f"{ip}#联通{count_m_cu}")
                    count_m_cu += 1
                elif remark.startswith('CT'): 
                    final_list.append(f"{ip}#电信{count_m_ct}")
                    count_m_ct += 1
                else: 
                    final_list.append(f"{ip}#其他{count_m_other}")
                    count_m_other += 1

    # 2. 测试模式源 (uouin.com) - 重点修改
    # 这里我们不使用全局去重，因为我们要看哪些模式成功了
    print("开始测试多种获取模式...")
    test_results = fetch_all_test_modes(url_selenium_target)
    
    # 将测试结果分类存入
    # 格式已经在函数里处理为: IP#模式名称_类型
    final_list.extend(test_results)

    # 3. 反代源
    real_sub_url = get_real_sub_url(url_sub_page)
    if real_sub_url:
        proxy_nodes = parse_proxy_nodes(real_sub_url)
        # 反代源也不去重了，为了测试方便
        final_list.extend(proxy_nodes)

    # 4. 文件输出
    # 为了方便你查看，我把所有结果都写入 ip.txt 和 cmip.txt
    # 另外单独生成一个 debug_modes.txt 专门看测试结果
    
    with open('cmip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_list))
    
    with open('ip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_list))
        
    # 分类输出 (简单关键词过滤)
    def save_keyword(keyword, filename):
        lines = [l for l in final_list if keyword in l]
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
    save_keyword("电信", "ct.txt")
    save_keyword("联通", "cu.txt")
    save_keyword("移动", "cm.txt")
    save_keyword("多线", "多线.txt") # 只有成功的模式才会包含“多线”
    save_keyword("IPV6", "ipv6.txt")
    save_keyword("反代IP", "反代.txt")
    
    # 专门的测试报告文件
    with open('测试报告.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(test_results))

if __name__ == "__main__":
    main()
