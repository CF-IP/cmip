import requests

def fetch_and_parse(url):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        content = response.text
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        return lines
    except:
        return []

def main():
    url_ct = "https://cf.090227.xyz/ct?ips=6"
    url_cu = "https://cf.090227.xyz/cu"
    url_cm = "https://cf.090227.xyz/cmcc?ips=8"
    url_other = "https://cf.090227.xyz/ip.164746.xyz"
    url_mixed = "https://cf.090227.xyz/CloudFlareYes"

    list_ct = []
    list_cu = []
    list_cm = []
    list_other = []
    
    count_ct = 0
    count_cu = 0
    count_cm = 0
    count_other = 0

    lines_ct = fetch_and_parse(url_ct)
    for line in lines_ct:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_ct += 1
            list_ct.append(f"{ip}#电信{count_ct}")

    lines_cu = fetch_and_parse(url_cu)
    for line in lines_cu:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_cu += 1
            list_cu.append(f"{ip}#联通{count_cu}")

    lines_cm = fetch_and_parse(url_cm)
    for line in lines_cm:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_cm += 1
            list_cm.append(f"{ip}#移动{count_cm}")

    lines_other = fetch_and_parse(url_other)
    for line in lines_other:
        if '#' in line:
            ip = line.split('#')[0].strip()
        else:
            ip = line.strip()
        if ip:
            count_other += 1
            list_other.append(f"{ip}#其他{count_other}")

    lines_mixed = fetch_and_parse(url_mixed)
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

    final_results = list_ct + list_cu + list_cm + list_other

    with open('cmip.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_results))

if __name__ == "__main__":
    main()
