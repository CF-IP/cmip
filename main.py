import requests
import base64
import re
import time
import json
from pyvirtualdisplay import Display

# 引入新工具库
try:
    from DrissionPage import ChromiumPage, ChromiumOptions
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

def extract_ip_from_text(text):
    # 从任意文本中提取所有合法IP
    ips = []
    # 简单的正则提取
    candidates = re.findall(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|[0-9a-fA-F:]{5,}', text)
    for ip in candidates:
        if is_valid_ip(ip):
            ips.append(ip)
    return ips

def fetch_content_requests(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.text
    except:
        return ""

# ================= 进阶测试模式 =================

def run_playwright_network_sniff(url):
    """
    模式A: 网络嗅探
    直接监听网页的所有 Response，寻找包含 IP 的 JSON 数据包
    """
    results = []
    debug_log = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            # 监听所有响应
            def handle_response(response):
                try:
                    # 尝试解析 JSON
                    if "json" in response.headers.get("content-type", ""):
                        data = response.json()
                        text_dump = json.dumps(data)
                        found_ips = extract_ip_from_text(text_dump)
                        if found_ips:
                            # 简单粗暴：如果 JSON 里包含 IP，我们假设它是数据源
                            # 这里暂时标记为 '嗅探数据'，后续可以细化解析
                            for ip in found_ips:
                                results.append(("嗅探数据", ip))
                except:
                    pass
            
            page.on("response", handle_response)
            
            page.goto(url)
            page.wait_for_timeout(20000) # 等待20秒，确保所有 API 加载完成
            
            title = page.title()
            debug_log.append(f"Page Title: {title}")
            
            browser.close()
    except Exception as e:
        debug_log.append(f"Error: {str(e)}")
        
    return results, debug_log

def run_playwright_source_scan(url):
    """
    模式B: 暴力源码扫描
    不依赖表格结构，直接获取整个网页 HTML，用正则暴力提取所有 IP
    """
    results = []
    debug_log = []
    
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True) # 使用 Firefox 内核
            page = browser.new_page()
            page.goto(url)
            page.wait_for_timeout(15000)
            
            # 获取整个页面 HTML
            content = page.content()
            debug_log.append(f"Content Length: {len(content)}")
            
            found_ips = extract_ip_from_text(content)
            for ip in found_ips:
                # 简单过滤，避免把版本号当IP
                if ip.count('.') == 3 or ':' in ip:
                    results.append(("源码扫描", ip))
            
            browser.close()
    except Exception as e:
        debug_log.append(f"Error: {str(e)}")
        
    return results, debug_log

def run_drission_iframe_scan(url):
    """
    模式C: DrissionPage 深度扫描
    尝试进入 iframe 查找
    """
    results = []
    debug_log = []
    display = None
    
    try:
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        
        co = ChromiumOptions()
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        
        page = ChromiumPage(co)
        page.get(url)
        time.sleep(15)
        
        debug_log.append(f"Title: {page.title}")
        
        # 1. 尝试常规表格
        rows = page.eles('tag:tr')
        for row in rows:
            cols = row.eles('tag:td')
            if len(cols) >= 3:
                lt = cols[1].text.strip()
                ip = cols[2].text.strip()
                if is_valid_ip(ip):
                    results.append((lt, ip))
        
        # 2. 如果没找到，尝试暴力扫描 body 文本
        if not results:
            text = page.html
            ips = extract_ip_from_text(text)
            for ip in ips:
                results.append(("DP暴力", ip))
                
    except Exception as e:
        debug_log.append(f"Error: {str(e)}")
    finally:
        try: page.quit()
        except: pass
        if display: display.stop()
        
    return results, debug_log

def fetch_all_test_modes(url):
    all_found = []
    report_logs = []
    
    # 1. 网络嗅探模式 (最强力，直接截获数据包)
    print("Running Mode: Playwright Network Sniffing...")
    data, logs = run_playwright_network_sniff(url)
    report_logs.extend(logs)
    report_logs.append(f"Sniffing Found: {len(data)}")
    for lt, ip in data:
        all_found.append(f"{ip}#Sniff_{lt}")

    # 2. 源码暴力扫描模式 (不信表格结构)
    print("Running Mode: Playwright Source Scan...")
    data, logs = run_playwright_source_scan(url)
    report_logs.extend(logs)
    report_logs.append(f"Source Scan Found: {len(data)}")
    for lt, ip in data:
        # 去重，如果刚才嗅探找到了就不加了
        if f"{ip}#Sniff" not in str(all_found):
            all_found.append(f"{ip}#Scan_{lt}")

    # 3. DrissionPage 混合模式
    print("Running Mode: DrissionPage Mixed...")
    data, logs = run_drission_iframe_scan(url)
    report_logs.extend(logs)
    report_logs.append(f"DP Found: {len(data)}")
    for lt, ip in data:
        if ip not in str(all_found):
            all_found.append(f"{ip}#DP_{lt}")
            
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

    # 2. 强力测试模式
    print("Start Advanced Scraping...")
    test_results, logs = fetch_all_test_modes(url_selenium_target)
    
    # 对测试结果进行简单去重和格式化
    for item in test_results:
        ip = item.split('#')[0]
        if is_valid_ip(ip) and ip not in seen_ips:
            seen_ips.add(ip)
            final_list.append(item)

    # 3. 反代源
    real_sub_url = get_real_sub_url(url_sub_page)
    if real_sub_url:
        proxy_nodes = parse_proxy_nodes(real_sub_url)
        for node in proxy_nodes:
            ip = node.split('#')[0]
            if is_valid_ip(ip) and ip not in seen_ips:
                seen_ips.add(ip)
                final_list.append(node)

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
    # 注意：如果网络嗅探成功，关键词可能是 Sniff_嗅探数据，所以这里把包含 Sniff 的也存入多线（暂存）
    # 或者你需要手动检查 ip.txt 看看新模式的后缀是什么，然后再分类
    save_keyword("多线", "多线.txt")
    save_keyword("Sniff", "多线.txt") # 暂时把嗅探到的放入多线，方便查看
    save_keyword("Scan", "多线.txt")  # 暂时把扫描到的放入多线
    save_keyword("IPV6", "ipv6.txt")
    save_keyword("反代IP", "反代.txt")
    
    with open('测试报告.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(logs))

if __name__ == "__main__":
    main()
