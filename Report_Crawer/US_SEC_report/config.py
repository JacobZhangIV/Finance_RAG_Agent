"""SEC 财报爬虫配置。"""
import os

# SEC 要求：User-Agent 需包含可联系到的邮箱
HEADERS = {
    "User-Agent": "Jacob hz3686@nyu.edu",
    "Accept-Encoding": "gzip, deflate",
}

# 路径（相对项目根目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TICKERS_JSON = os.path.join(BASE_DIR, "company_tickers.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
FILINGS_DIR = os.path.join(DATA_DIR, "filings")
SUBMISSIONS_DIR = os.path.join(DATA_DIR, "submissions")

# 财报类型：优先 10-K，其次 10-Q
DEMO_FORMS = ("10-K", "10-Q",'20-F','8-K','6-K','DEF 14A','S-1')

# 请求间隔（秒），避免触发 SEC 限流
REQUEST_DELAY = 0.3

# 下载公司数量
LIMIT = 50

# 每家公司最多下载的财报份数（10-K/10-Q，按时间从新到旧取）
REPORTS_PER_COMPANY = 50

# 语料与 RAG
CORPUS_DIR = os.path.join(DATA_DIR, "corpus")
# 单条 chunk 文本最大字符数（便于嵌入模型限制），过长则截断；None 表示不截断
EMBEDDING_MAX_CHARS = 8000