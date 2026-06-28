import os
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

API_URL = "https://api.binjie.fun/api/generateStream"
USER_ID = "exam-agent-user"
MAX_CONCURRENCY = 3
MAX_RETRIES = 3
RETRY_DELAY = 2

SPLITTER_SYSTEM = """تو یک دستیار هوشمند هستی. وظیفه تو جدا کردن سوالات از یک متن امتحانی است.
قوانین:
- فقط JSON خروجی بده
- بدون مارکداون
- بدون هیچ توضیح اضافه
فرمت خروجی دقیقا این باشد:
[{"id":1,"question":"متن سوال"},{"id":2,"question":"متن سوال"}]"""

SOLVER_SYSTEM = """تو یک معلم باتجربه هستی. سوال را حل کن.
قوانین:
- فقط JSON خروجی بده
- بدون مارکداون
- بدون هیچ توضیح اضافه
فرمت خروجی دقیقا این باشد:
{"question":"متن سوال","steps":["گام ۱","گام ۲",...],"final_answer":"جواب نهایی","confidence":85}"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("exam-agent")