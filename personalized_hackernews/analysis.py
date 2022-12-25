from urllib.parse import urlparse
from collections import Counter


robots = [_a for _a in a if 'robot' in _a['title'][0]]
domains = [urlparse(_a['href'][0]).netloc for _a in a]