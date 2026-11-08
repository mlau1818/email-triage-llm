"""
Rule-based extraction of structured fields from an email (no model needed):
requester, due date, money amounts and reference IDs.
Also maps a due date to an urgency level.
"""
import re

CLOSINGS = r"(?:Thanks|Thank you|Best|Best regards|Regards|Cheers|Kind regards)"
WEEKDAYS = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"

# Ordered: the first pattern that matches wins (more specific first).
DUE_PATTERNS = [
    r"\bASAP\b",
    r"\bEOD today\b",
    r"\bend of (?:the )?day\b",
    r"\btoday(?: \d{1,2}(?::\d{2})? ?[AP]M)?\b",
    r"\btomorrow(?: morning| afternoon| EOD)?\b",
    r"\bin \d+ hours?\b",
    r"\bend of (?:the )?(?:week|month|quarter)\b",
    r"\bnext week\b",
    rf"(?<=\bby ){WEEKDAYS}\b",
    rf"(?<=\bby ){MONTHS} \d{{1,2}}\b",
    r"(?<=\bby )\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
]

HIGH_DUE = re.compile(r"ASAP|EOD|end of (the )?day|today|tomorrow|hours?", re.I)
MEDIUM_DUE = re.compile(rf"{WEEKDAYS}|{MONTHS} \d|\d/\d|end of (the )?week", re.I)
LOW_DUE = re.compile(r"end of (the )?(month|quarter)|next week", re.I)
NO_RUSH = re.compile(r"no rush|when(ever)? you (have|get) a chance|no action (needed|required)|"
                     r"nothing to do|for your information|\bFYI\b", re.I)

AMOUNT_RE = re.compile(r"\$\d[\d,]*(?:\.\d+)?[KMB]?\b")
ID_RE = re.compile(r"\b(?:PO|CC|REQ|INC)-?\d{4,}\b")


def split_email(text):
    """Return (sender_from_header, subject, body). Header lines are optional."""
    sender, subject = "", ""
    lines = text.strip().splitlines()
    body_start = 0
    for i, line in enumerate(lines[:4]):
        m_from = re.match(r"^From:\s*(.+?)\s*(?:<.*>)?\s*$", line)
        m_subj = re.match(r"^Subject:\s*(.*)$", line)
        if m_from:
            sender, body_start = m_from.group(1).strip(), i + 1
        elif m_subj:
            subject, body_start = m_subj.group(1).strip(), i + 1
    body = "\n".join(lines[body_start:]).strip()
    return sender, subject, body


def extract_requester(text):
    sender, _, body = split_email(text)
    if sender:
        return sender
    # Fall back to the line right after the closing ("Thanks,\nMaria Lopez")
    m = re.search(rf"^{CLOSINGS},?\s*\n\s*([A-Z][\w'\-]+(?: [A-Z][\w'\-]+)*)\s*$", body, re.M)
    if m:
        return m.group(1).strip()
    # Last resort: a name alone on the last line ("...thanks!\n\nKaren Hill")
    last = body.strip().splitlines()[-1].strip() if body.strip() else ""
    if re.fullmatch(r"[A-Z][\w'\-]+(?: [A-Z][\w'\-]+){0,2}", last):
        return last
    return ""


def extract_due_date(text):
    for pattern in DUE_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(0)
    return ""


def extract_amounts(text):
    return AMOUNT_RE.findall(text)


def extract_ids(text):
    seen = []
    for x in ID_RE.findall(text):
        if x not in seen:
            seen.append(x)
    return seen


def urgency_from_rules(text, due_date):
    """Urgency implied by explicit wording. Returns None when the text gives no clear signal."""
    if due_date:
        if HIGH_DUE.search(due_date):
            return "High"
        if LOW_DUE.search(due_date):
            return "Low"
        if MEDIUM_DUE.search(due_date):
            return "Medium"
    if re.search(r"\burgent(ly)?\b", text, re.I):
        return "High"
    if NO_RUSH.search(text):
        return "Low"
    return None


def extract_fields(text):
    return {
        "requester": extract_requester(text),
        "due_date": extract_due_date(text),
        "amounts": extract_amounts(text),
        "ids": extract_ids(text),
    }
