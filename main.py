import requests
import base64
import re
import time
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ================= 工具函数 =================

def is_valid_ip(ip):
    if not ip or len(ip) < 7:
        return False
    if '0.00%' in ip or '正在' in ip or '获取' in ip:
        return False
    # 过滤时间戳
    if re.match(r'^\d{2}:\d{2}:\d{2}$', ip):
        return False
    # IPv4
    if re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return True
    # IPv6
    if ip.count(':') >= 2 and re.match(r'^[0-9a-fA-F:]+$', ip):
        return True
    return False

def fetch_content_requests(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.text
    except:
        return ""

# ================= 核心抓取逻辑 =================

def fetch_uouin_data(url):
    results = []
    debug_log = []
    
    try:
        with sync_playwright() as p:
            # 继续使用 Firefox，因为它已经证明能成功加载页面
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url)
            
            # 等待表格加载
            try:
                page.wait_for_selector('table', timeout=25000)
            except:
                time.sleep(5)
            
            content = page.content()
            debug_log.append(f"Got content, length: {len(content)}")
            
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            
            debug_log.append(f"Found {len(rows)} rows")
            
            # === 详细调试日志 ===
            for i, row in enumerate(rows):
                cols = row.find_all('td')
                # 打印每一列的内容，方便定位
                row_text = [c.get_text(strip=True) for c in cols]
                debug_log.append(f"Row {i}: {row_text}")
                
                # 尝试多种列组合，防止列偏移
                if len(cols) >= 3:
                    # 假设标准结构: [序号, 线路, IP, ...]
                    line_name = cols[1].get_text(strip=True)
                    ip_addr = cols[2].get_text(strip=True)
                    
                    # 兜底检测: 如果第2列看起来像IP，说明列偏移了
                    if is_valid_ip(line_name) and not is_valid_ip(ip_addr):
                         # 交换
                         temp = line_name
                         line_name = cols[0].get_text(strip=True) # 可能是前一列
                         ip_addr = temp
                         debug_log.append(f"  -> Detected column shift, adjusted IP to: {ip_addr}")

                    if is_valid_ip(ip_addr):
                        results.append((line_name, ip_addr))
                        debug_log.append(f"  -> Extracted: [{line_name}] - [{ip_addr}]")
                    else:
                        debug_log.append(f"  -> Invalid IP skipped: {ip_addr}")
            
            browser.close()
            
    except Exception as e:
        debug_log.append(f"Error: {str(e)}")
        
    return results, debug_log

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

def fetch_and_parse_lines(url):
    content = fetch_content_requests(url)
    if not content:
        return []
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    return lines

# ================= 主程序 =================

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
    
    # 计数器
    count_ct = 0
    count_cu = 0
    count_cm = 0
    count_other = 0
    count_multi = 0
    count_ipv6 = 0
    
    # 1. 处理 API.UOUIN.COM
    uouin_data, logs = fetch_uouin_data(url_selenium_target)
    
    all_nodes = [] 

    # 处理 Uouin 数据
    for line_name, ip in uouin_data:
        if ip in seen_ips: continue
        seen_ips.add(ip)
        
        l_name = line_name.upper()
        # 宽容匹配
        if "电信" in l_name: all_nodes.append({'ip': ip, 'type': 'ct'})
        elif "联通" in l_name: all_nodes.append({'ip': ip, 'type': 'cu'})
        elif "移动" in l_name: all_nodes.append({'ip': ip, 'type': 'cm'})
        elif "多线" in l_name: all_nodes.append({'ip': ip, 'type': 'multi'})
        elif "IPV6" in l_name: all_nodes.append({'ip': ip, 'type': 'ipv6'})
        else: 
            # 这里的 fallback 很重要，如果什么都没匹配到，暂时归为 other，并在日志里体现
            all_nodes.append({'ip': ip, 'type': 'other'})

    # 2. 处理常规源
    def process_url(url, type_code):
        lines = fetch_and_parse_lines(url)
        for line in lines:
            if '#' in line: ip = line.split('#')[0].strip()
            else: ip = line.strip()
            if is_valid_ip(ip) and ip not in seen_ips:
                seen_ips.add(ip)
                all_nodes.append({'ip': ip, 'type': type_code})
    
    process_url(url_ct, "ct")
    process_url(url_cu, "cu")
    process_url(url_cm, "cm")
    process_url(url_other, "other")
    
    # 3. Mixed 源
    lines_mixed = fetch_and_parse_lines(url_mixed)
    for line in lines_mixed:
        if '#' in line:
            parts = line.split('#')
            ip = parts[0].strip()
            remark = parts[1].strip().upper()
            if is_valid_ip(ip) and ip not in seen_ips:
                seen_ips.add(ip)
                if remark.startswith('CM'): all_nodes.append({'ip': ip, 'type': 'cm'})
                elif remark.startswith('CU'): all_nodes.append({'ip': ip, 'type': 'cu'})
                elif remark.startswith('CT'): all_nodes.append({'ip': ip, 'type': 'ct'})
                else: all_nodes.append({'ip': ip, 'type': 'other'})

    # 4. 反代源
    real_sub_url = get_real_sub_url(url_sub_page)
    if real_sub_url:
        proxy_nodes = parse_proxy_nodes(real_sub_url)
        for node in proxy_nodes:
            ip = node.split('#')[0]
            if ip in seen_ips: continue
            seen_ips.add(ip)
            remark = node.split('#')[1]
            all_nodes.append({'ip': ip, 'type': 'proxy', 'remark': remark})

    # 5. 生成文件
    list_ct = []
    list_cu = []
    list_cm = []
    list_other = []
    list_multi = []
    list_ipv6 = []
    list_proxy = []

    for node in all_nodes:
        t = node['type']
        ip = node['ip']
        
        if t == 'ct':
            count_ct += 1
            list_ct.append(f"{ip}#电信{count_ct}")
        elif t == 'cu':
            count_cu += 1
            list_cu.append(f"{ip}#联通{count_cu}")
        elif t == 'cm':
            count_cm += 1
            list_cm.append(f"{ip}#移动{count_cm}")
        elif t == 'other':
            count_other += 1
            list_other.append(f"{ip}#其他{count_other}")
        elif t == 'multi':
            count_multi += 1
            list_multi.append(f"{ip}#多线{count_multi}")
        elif t == 'ipv6':
            count_ipv6 += 1
            list_ipv6.append(f"{ip}#IPV6-{count_ipv6}")
        elif t == 'proxy':
            list_proxy.append(f"{ip}#{node['remark']}")

    final_all = list_ct + list_cu + list_cm + list_other + list_multi + list_ipv6 + list_proxy

    with open('cmip.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(final_all))
    with open('ip.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(final_all))
    with open('ct.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(list_ct))
    with open('cu.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(list_cu))
    with open('cm.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(list_cm))
    with open('多线.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(list_multi))
    with open('ipv6.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(list_ipv6))
    with open('反代.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(list_proxy))
        
    with open('测试报告.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(logs))

if __name__ == "__main__":
    main()
