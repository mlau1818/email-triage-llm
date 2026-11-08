"""
Email triage + extraction with small pre-trained language models (no training needed).

  - Category  : zero-shot classification with an NLI model (facebook/bart-large-mnli)
  - Urgency   : same zero-shot model; in "hybrid" mode explicit wording (ASAP, by Friday,
                no rush...) found by rules takes priority over the model
  - Summary   : instruction-tuned seq2seq model (google/flan-t5-base)
  - Tasks     : same flan-t5 model, asked for the list of actions requested
  - Requester, due date, amounts, IDs : rule-based extractors (extractors.py)
"""
import re

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

from extractors import extract_fields, split_email, urgency_from_rules

ZERO_SHOT_MODEL = "facebook/bart-large-mnli"
GEN_MODEL = "google/flan-t5-base"

# Category name -> description the NLI model checks ("This email is <description>.")
CATEGORY_DESCRIPTIONS = {
    "Report Request": "asking someone to send or prepare a report",
    "Data Correction": "reporting wrong numbers in a report that need to be corrected",
    "Access Request": "asking for access or permissions to a system, dashboard or folder",
    "Approval Request": "asking for approval of a purchase order, invoice or budget",
    "Ad-hoc Analysis": "asking for an analysis or explanation of a variance, gap or trend",
    "Meeting Request": "asking to schedule a meeting or a call",
    "FYI / No Action": "only sharing information, with no action required",
}

URGENCY_DESCRIPTIONS = {
    "High": "urgent and must be done today or immediately",
    "Medium": "due in the next few days or this week",
    "Low": "not urgent, with no rush or a deadline weeks away",
}

URGENCY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


class EmailTriage:
    def __init__(self, zero_shot_model=ZERO_SHOT_MODEL, gen_model=GEN_MODEL,
                 urgency_mode="hybrid", device=None):
        """urgency_mode: 'hybrid' (rules first, model as fallback) or 'model' (model only)."""
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.urgency_mode = urgency_mode
        self.classifier = pipeline("zero-shot-classification", model=zero_shot_model, device=device)
        # flan-t5 is loaded directly (the text2text pipeline was removed in transformers 5)
        self.tokenizer = AutoTokenizer.from_pretrained(gen_model)
        self.gen_model = AutoModelForSeq2SeqLM.from_pretrained(gen_model).to(device).eval()

    # ---------- model calls ----------
    def _zero_shot(self, texts, descriptions):
        labels = list(descriptions.keys())
        candidates = list(descriptions.values())
        outputs = self.classifier(texts, candidate_labels=candidates,
                                  hypothesis_template="This email is {}.", batch_size=16)
        if isinstance(outputs, dict):
            outputs = [outputs]
        results = []
        for out in outputs:
            scores = {labels[candidates.index(lbl)]: round(float(s), 4)
                      for lbl, s in zip(out["labels"], out["scores"])}
            results.append(scores)
        return results

    @torch.no_grad()
    def _generate(self, prompts, max_new_tokens=60, batch_size=16):
        outputs = []
        for i in range(0, len(prompts), batch_size):
            batch = self.tokenizer(prompts[i:i + batch_size], return_tensors="pt", padding=True,
                                   truncation=True, max_length=512).to(self.device)
            ids = self.gen_model.generate(**batch, max_new_tokens=max_new_tokens, num_beams=2)
            outputs += [t.strip() for t in self.tokenizer.batch_decode(ids, skip_special_tokens=True)]
        return outputs

    @staticmethod
    def _split_tasks(text):
        parts = re.split(r"\n|;|\s*\d+[.)]\s+|\s+-\s+", text)
        tasks = [p.strip(" .-•") for p in parts if p and len(p.strip(" .-•")) > 3]
        return list(dict.fromkeys(tasks))  # dedupe, keep order

    # ---------- public API ----------
    def triage_batch(self, emails):
        """Process a list of raw email texts. Returns a list of result dicts."""
        cleaned = []
        for e in emails:
            _, subject, body = split_email(e)
            cleaned.append(f"Subject: {subject}\n{body}" if subject else body)

        cat_scores = self._zero_shot(cleaned, CATEGORY_DESCRIPTIONS)
        urg_scores = self._zero_shot(cleaned, URGENCY_DESCRIPTIONS)
        summaries = self._generate(
            [f"Summarize this email in one sentence.\n\n{t}" for t in cleaned])
        task_texts = self._generate(
            [f"What does the sender ask the recipient to do? List the actions.\n\n{t}"
             for t in cleaned])

        results = []
        for raw, cs, us, summ, tt in zip(emails, cat_scores, urg_scores, summaries, task_texts):
            fields = extract_fields(raw)
            category = max(cs, key=cs.get)
            model_urgency = max(us, key=us.get)

            urgency, source = model_urgency, "model"
            if self.urgency_mode == "hybrid":
                rule_urgency = urgency_from_rules(raw, fields["due_date"])
                if rule_urgency:
                    urgency, source = rule_urgency, "rules"
            if category == "FYI / No Action":
                urgency, source = "Low", "category"

            tasks = [] if category == "FYI / No Action" else self._split_tasks(tt)
            results.append({
                "category": category,
                "category_scores": cs,
                "urgency": urgency,
                "urgency_source": source,
                "urgency_model": model_urgency,
                "urgency_scores": us,
                "summary": summ,
                "tasks": tasks,
                **fields,
            })
        return results

    def triage(self, email):
        return self.triage_batch([email])[0]


def sort_by_urgency(results):
    """Return indices ordered High -> Medium -> Low (stable)."""
    return sorted(range(len(results)), key=lambda i: URGENCY_ORDER[results[i]["urgency"]])
