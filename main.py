import requests
import base64
import re
import time

def fetch_content(url, retries=3):
    for i in range(retries):
        try:
            response = requests.get(url, timeout=15)
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
                        if len(remark) >= 2 and remark[0:2].isalpha():
                            code = remark[0:2].upper()
                            nodes.append(f"{ip}#{code}（反代IP）")
            except:
                continue
                
    return nodes

def main():
    url_ct = "https://cf.090227.xyz/ct?ips=6"
    url_cu = "https://cf.090227.xyz/cu"
    url_cm = "https://cf.090227.xyz/cmcc?ips=8"
    url_other = "https://cf.090227.xyz/ip.164746.xyz"
    url_mixed = "https://cf.090227.xyz/CloudFlareYes"
    url_sub_page = "https://getsub.classelivre.eu.org/sub"

    list_ct = []
    list_cu = []
    list_cm = []
    list_other = []
    list_proxy = []
    
    count_ct = 0
    count_cu = 0
    count_cm = 0
    count_other = 0

    lines_ct = fetch_and_parse_lines(url_ct)
    for line in lines_ct:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_ct += 1
            list_ct.append(f"{ip}#电信{count_ct}")

    lines_cu = fetch_and_parse_lines(url_cu)
    for line in lines_cu:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_cu += 1
            list_cu.append(f"{ip}#联通{count_cu}")

    lines_cm = fetch_and_parse_lines(url_cm)
    for line in lines_cm:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_cm += 1
            list_cm.append(f"{ip}#移动{count_cm}")

    lines_other = fetch_and_parse_lines(url_other)
    for line in lines_other:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_other += 1
            list_other.append(f"{ip}#其他{count_other}")

    lines_mixed = fetch_and_parse_lines(url_mixed)
    for line in lines_mixed:
        if '#' in line:
            parts = line.split('#')
            ip = parts[0].strip()
            remark = parts[1].strip().upper()
            
            if remark.startswith('CM'):
                count_cm += 1
                list_cm.append(f"{ip}#移动{count_cm}")
            elif remark.startswith('CU'):
                count_cu += 1
                list_cu.append(f"{ip}#联通{count_cu}")
            elif remark.startswith('CT'):
                count_ct += 1
                list_ct.append(f"{ip}#电信{count_ct}")

    real_sub_url = get_real_sub_url(url_sub_page)
    if real_sub_url:
        proxy_nodes = parse_proxy_nodes(real_sub_url)
        list_proxy.extend(proxy_nodes)

    final_results = list_ct + list_cu + list_cm + list_other + list_proxy

    with open('cmip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_results))

if __name__ == "__main__":
    main()
