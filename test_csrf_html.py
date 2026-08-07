import urllib.request
import re

try:
    req = urllib.request.Request('http://127.0.0.1:8000/login/')
    res = urllib.request.urlopen(req)
    html = res.read().decode('utf-8')
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', html)
    if m:
        print('Token found:', m.group(1), 'Length:', len(m.group(1)))
    else:
        print('Token not found in login page')
except Exception as e:
    print('Error:', e)
