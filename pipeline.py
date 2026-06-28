import json
import os
import re
import time
import logging
import requests
import pdfplumber
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    log, API_URL, USER_ID, MAX_CONCURRENCY,
    MAX_RETRIES, RETRY_DELAY, CACHE_DIR,
    SPLITTER_SYSTEM, SOLVER_SYSTEM,
)

# ── مرحله ۱: خواندن PDF ──────────────────────────────────────────

def extract_text(pdf_path: str) -> str:
    log.info("استخراج متن از PDF...")
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())
                else:
                    log.warning("صفحه %d خالی بود - OCR نیاز است (پشتیبانی نمی‌شود)", i + 1)
    except Exception as e:
        log.error("خطا در خواندن PDF: %s", e)
        raise
    full_text = "\n\n".join(text_parts)
    log.info("تعداد کاراکترهای استخراج‌شده: %d", len(full_text))
    return full_text


# ── مرحله ۲: پاکسازی متن ─────────────────────────────────────────

def clean_text(raw: str) -> str:
    log.info("پاکسازی متن...")
    text = raw
    text = re.sub(r"^\s*صفحه\s*\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[‌]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    log.info("متن پس از پاکسازی: %d کاراکتر", len(text))
    return text


# ── مرحله ۳: جدا کردن سوالات با AI ──────────────────────────────

def _call_api(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "userId": USER_ID,
        "network": False,
        "withoutContext": True,
        "stream": False,
    }
    resp = requests.post(API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.text


def _parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def split_questions(clean_text: str) -> list[dict]:
    cache_path = os.path.join(CACHE_DIR, "questions.json")
    if os.path.exists(cache_path):
        log.info("بارگذاری سوالات از کش...")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    log.info("ارسال به AI برای جدا کردن سوالات...")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = _call_api(SPLITTER_SYSTEM, clean_text)
            questions = _parse_json(raw)
            if not isinstance(questions, list) or not questions:
                raise ValueError("خروجی لیست خالی یا نامعتبر")
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            log.info("تعداد سوالات شناسایی‌شده: %d", len(questions))
            return questions
        except Exception as e:
            log.warning("تلاش %d/%d ناموفق: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
    raise RuntimeError("جدا کردن سوالات پس از چند تلاش ناموفق بود")


# ── مرحله ۴: حل هر سوال با AI ───────────────────────────────────

def solve_one(question: dict) -> dict:
    qid = question["id"]
    cache_path = os.path.join(CACHE_DIR, f"answer_{qid}.json")

    if os.path.exists(cache_path):
        log.info("سوال %d از کش بارگذاری شد", qid)
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    q_text = question["question"]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = _call_api(SOLVER_SYSTEM, q_text)
            result = _parse_json(raw)
            result["id"] = qid
            result["question"] = q_text
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            log.info("سوال %d حل شد (اطمینان: %s%%)", qid, result.get("confidence", "?"))
            return result
        except Exception as e:
            log.warning("حل سوال %d - تلاش %d/%d خطا: %s", qid, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    fallback = {"id": qid, "question": q_text, "steps": ["خطا در حل"], "final_answer": "نامشخص", "confidence": 0}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(fallback, f, ensure_ascii=False, indent=2)
    return fallback


def solve_all(questions: list[dict]) -> list[dict]:
    results = []
    solved_ids = set()
    cache_files = [f for f in os.listdir(CACHE_DIR) if f.startswith("answer_") and f.endswith(".json")]
    for cf in cache_files:
        try:
            with open(os.path.join(CACHE_DIR, cf), "r", encoding="utf-8") as f:
                d = json.load(f)
                results.append(d)
                solved_ids.add(d["id"])
        except Exception:
            pass

    remaining = [q for q in questions if q["id"] not in solved_ids]
    if remaining:
        log.info("حل %d سوال با موازی‌سازی (حداکثر %d همزمان)...", len(remaining), MAX_CONCURRENCY)
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
            futures = {pool.submit(solve_one, q): q for q in remaining}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    q = futures[future]
                    log.error("شکست در حل سوال %d: %s", q["id"], e)

    results.sort(key=lambda x: x["id"])
    return results


# ── مرحله ۵: تجمیع ───────────────────────────────────────────────

def aggregate(answers: list[dict]) -> dict:
    total_confidence = sum(a.get("confidence", 0) for a in answers)
    avg = round(total_confidence / len(answers), 1) if answers else 0
    return {
        "count": len(answers),
        "average_confidence": avg,
        "questions": answers,
    }