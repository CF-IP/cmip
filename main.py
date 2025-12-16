import requests
import base64
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def is_valid_ip(ip):
    # IPv4 验证
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    # IPv6 验证 (简单版)
    ipv6_pattern = r'^[0-9a-fA-F:]+$'
    
    if re.match(ipv4_pattern, ip):
        return True
    if ':' in ip and re.match(ipv6_pattern, ip):
        return True
    return False

def fetch_content(url, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except:
            time.sleep(2)
    return ""

def fetch_and_parse_lines(url):
    content = fetch_content(url)
    if not content:
        return []
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    return lines

def get_real_sub_url(page_url):
    html = fetch_content(page_url, retries=5)
    if not html:
        return None
    
    urls = re.findall(r'https?://[^\s"\'<>]+', html)
    
    target_urls = [u for u in urls if '?uuid=' in u]
    if target_urls:
        return target_urls[0]
    
    if urls:
        return max(urls, key=len)
    
    return None

def fetch_selenium_data(url):
    results = []
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        time.sleep(12)  # 增加等待时间以应对加载延迟
        
        rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                line_type = cols[1].text.strip()
                ip = cols[2].text.strip()
                
                # 严格校验 IP 格式
                if ip and is_valid_ip(ip):
                    results.append((line_type, ip))
    except:
        pass
    finally:
        if driver:
            driver.quit()
    return results

def parse_proxy_nodes(sub_url):
    content = fetch_content(sub_url, retries=3)
    if not content:
        return []

    try:
        missing_padding = len(content) % 4
        if missing_padding:
            content += '=' * (4 - missing_padding)
        decoded_data = base64.b64decode(content).decode('utf-8', errors='ignore')
    except:
        return []

    nodes = []
    lines = decoded_data.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('vless://'):
            try:
                main_part = line.replace('vless://', '')
                
                if '#' in main_part:
                    config_part, remark = main_part.split('#', 1)
                else:
                    config_part = main_part
                    remark = ""
                
                remark = requests.utils.unquote(remark).strip()
                
                if '@' in config_part:
                    user_info, host_info = config_part.split('@', 1)
                    
                    if '?' in host_info:
                        address_part = host_info.split('?')[0]
                    else:
                        address_part = host_info
                    
                    if ':' in address_part:
                        ip = address_part.split(':')[0]
                        port = address_part.split(':')[1]
                    else:
                        continue 

                    if port == '443':
                        if len(remark) >= 2 and re.match(r'^[A-Za-z]{2}', remark):
                            code = remark[0:2].upper()
                            if is_valid_ip(ip):
                                nodes.append((ip, code))
            except:
                continue
                
    return nodes

def main():
    url_ct = "https://cf.090227.xyz/ct?ips=6"
    url_cu = "https://cf.090227.xyz/cu"
    url_cm = "https://cf.090227.xyz/cmcc?ips=8"
    url_other = "https://cf.090227.xyz/ip.164746.xyz"
    url_mixed = "https://cf.090227.xyz/CloudFlareYes"
    url_selenium = "https://api.uouin.com/cloudflare.html"
    url_sub_page = "https://getsub.classelivre.eu.org/sub"

    list_ct = []
    list_cu = []
    list_cm = []
    list_other = []
    list_multi = []
    list_ipv6 = []
    list_proxy = []

    count_ct = 0
    count_cu = 0
    count_cm = 0
    count_other = 0
    count_multi = 0
    count_ipv6 = 0

    seen_ips = set()

    def is_new_ip(ip_addr):
        if not is_valid_ip(ip_addr):
            return False
        if ip_addr in seen_ips:
            return False
        seen_ips.add(ip_addr)
        return True

    lines_ct = fetch_and_parse_lines(url_ct)
    for line in lines_ct:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip and is_new_ip(ip):
            count_ct += 1
            list_ct.append(f"{ip}#电信{count_ct}")

    lines_cu = fetch_and_parse_lines(url_cu)
    for line in lines_cu:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip and is_new_ip(ip):
            count_cu += 1
            list_cu.append(f"{ip}#联通{count_cu}")

    lines_cm = fetch_and_parse_lines(url_cm)
    for line in lines_cm:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip and is_new_ip(ip):
            count_cm += 1
            list_cm.append(f"{ip}#移动{count_cm}")

    lines_other = fetch_and_parse_lines(url_other)
    for line in lines_other:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip and is_new_ip(ip):
            count_other += 1
            list_other.append(f"{ip}#其他{count_other}")

    lines_mixed = fetch_and_parse_lines(url_mixed)
    for line in lines_mixed:
        if '#' in line:
            parts = line.split('#')
            ip = parts[0].strip()
            remark = parts[1].strip().upper()
            
            if is_new_ip(ip):
                if remark.startswith('CM'):
                    count_cm += 1
                    list_cm.append(f"{ip}#移动{count_cm}")
                elif remark.startswith('CU'):
                    count_cu += 1
                    list_cu.append(f"{ip}#联通{count_cu}")
                elif remark.startswith('CT'):
                    count_ct += 1
                    list_ct.append(f"{ip}#电信{count_ct}")
                else:
                    count_other += 1
                    list_other.append(f"{ip}#其他{count_other}")

    selenium_data = fetch_selenium_data(url_selenium)
    for line_type, ip in selenium_data:
        if is_new_ip(ip):
            if "移动" in line_type:
                count_cm += 1
                list_cm.append(f"{ip}#移动{count_cm}")
            elif "联通" in line_type:
                count_cu += 1
                list_cu.append(f"{ip}#联通{count_cu}")
            elif "电信" in line_type:
                count_ct += 1
                list_ct.append(f"{ip}#电信{count_ct}")
            elif "多线" in line_type:
                count_multi += 1
                list_multi.append(f"{ip}#多线{count_multi}")
            elif "IPV6" in line_type:
                count_ipv6 += 1
                list_ipv6.append(f"{ip}#IPV6-{count_ipv6}")
            else:
                count_other += 1
                list_other.append(f"{ip}#其他{count_other}")

    real_sub_url = get_real_sub_url(url_sub_page)
    if real_sub_url:
        proxy_data = parse_proxy_nodes(real_sub_url)
        for ip, code in proxy_data:
            if is_new_ip(ip):
                list_proxy.append(f"{ip}#{code}（反代IP）")

    final_all = list_ct + list_cu + list_cm + list_other + list_multi + list_ipv6 + list_proxy

    with open('cmip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_all))
        
    with open('ip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_all))

    with open('ct.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(list_ct))

    with open('cu.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(list_cu))

    with open('cm.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(list_cm))
    
    with open('多线.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(list_multi))

    with open('ipv6.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(list_ipv6))

    with open('反代.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(list_proxy))

if __name__ == "__main__":
    main()
