"""
Generate a synthetic dataset of request emails received by a finance / data team.

Each email comes with its ground-truth labels so the triage system can be evaluated:
  - category      : type of request (7 classes)
  - urgency       : High / Medium / Low
  - requester     : person who sent the request
  - due_date      : deadline as written in the email ("" if none)
  - amounts       : money amounts mentioned (separated by ";")
  - ids           : reference IDs mentioned (PO-, CC-, REQ-), separated by ";"
  - tasks         : reference list of the actions requested (separated by ";")

Usage:
    python src/generate_data.py            # writes data/emails.csv (seed 42, 140 emails)
    python src/generate_data.py --n 300 --seed 7 --out data/emails_big.csv
"""
import argparse
import csv
import os
import random

CATEGORIES = [
    "Report Request",
    "Data Correction",
    "Access Request",
    "Approval Request",
    "Ad-hoc Analysis",
    "Meeting Request",
    "FYI / No Action",
]

# (phrase written in the email, due_date label, urgency)
DEADLINES = {
    "High": [
        ("by EOD today", "EOD today"),
        ("ASAP", "ASAP"),
        ("by today 3 PM", "today 3 PM"),
        ("by tomorrow morning", "tomorrow morning"),
        ("urgently, before the close call in 2 hours", "in 2 hours"),
    ],
    "Medium": [
        ("by Friday", "Friday"),
        ("by Wednesday", "Wednesday"),
        ("by Nov 14", "Nov 14"),
        ("by 11/20", "11/20"),
        ("by end of week", "end of week"),
    ],
    "Low": [
        ("by end of month", "end of month"),
        ("sometime next week", "next week"),
        ("whenever you have a chance, no rush", ""),
        ("when you get a chance", ""),
    ],
}

PEOPLE = [
    ("Maria Lopez", "Finance Manager"), ("John Carter", "Controller"),
    ("Priya Natarajan", "FP&A Analyst"), ("David Kim", "Operations Lead"),
    ("Sofia Rossi", "Procurement Specialist"), ("Ahmed Hassan", "Program Manager"),
    ("Emily Chen", "Business Analyst"), ("Carlos Mendez", "Plant Finance Lead"),
    ("Hannah Muller", "Senior Accountant"), ("Lucas Silva", "Data Engineer"),
    ("Olivia Brown", "HR Business Partner"), ("Kenji Tanaka", "Supply Chain Manager"),
]
TEAM_MEMBERS = ["Ana", "Luis", "Daniela", "Jorge", "team"]
PERIODS = ["Q3", "October", "September", "Q3 YTD", "week 44", "November MTD"]
REPORTS = ["spending report", "variance report", "headcount report",
           "capex tracker", "opex summary", "inventory aging report"]
BUS = ["the Costa Rica site", "the Assembly & Test group", "Supply Chain",
       "the Fab operations team", "Corporate IT", "the LATAM region"]
MEETINGS = ["QBR deck", "staff meeting", "monthly business review",
            "budget review", "leadership update"]
SYSTEMS = ["Power BI spending", "SAP cost center", "Tableau capex",
           "SharePoint finance", "Snowflake reporting"]
VENDORS = ["Acme Industrial", "Delta Logistics", "BlueSky Consulting",
           "Nova Tools", "Prime Facilities"]
METRICS = ["opex", "freight cost", "overtime spend", "material cost", "utilities spend"]
TOPICS = ["the Q4 forecast", "the new allocation model", "the dashboard redesign",
          "the cost center cleanup", "the capex reforecast"]
SYSTEM_DOWN = ["the SAP reporting server", "the Power BI gateway", "the finance SharePoint"]


def money(rng):
    style = rng.random()
    if style < 0.5:
        return f"${rng.randint(1_000, 250_000):,}.{rng.choice(['00', '50', '75'])}"
    if style < 0.8:
        return f"${rng.randint(10, 950)}K"
    return f"${rng.randint(1, 9)}.{rng.randint(1, 9)}M"


def po(rng):
    return f"PO-{rng.randint(100000, 999999)}"


def cc(rng):
    return f"CC-{rng.randint(1000, 9999)}"


def req(rng):
    return f"REQ-{rng.randint(10000, 99999)}"


def build_email(category, rng):
    """Return (subject, body_without_signature, urgency, due_date, amounts, ids, tasks)."""
    urgency = rng.choices(["High", "Medium", "Low"], weights=[0.3, 0.4, 0.3])[0]
    if category == "FYI / No Action":
        urgency = "Low"
    phrase, due = rng.choice(DEADLINES[urgency])
    amounts, ids, tasks = [], [], []

    if category == "Report Request":
        period, report, bu, mtg = (rng.choice(PERIODS), rng.choice(REPORTS),
                                   rng.choice(BUS), rng.choice(MEETINGS))
        variant = rng.randint(0, 2)
        if variant == 0:
            subject = f"{period} {report} for {bu}"
            body = (f"Hi team,\n\nCould you please send me the {period} {report} for {bu}? "
                    f"I need it {phrase} for the {mtg}.")
        elif variant == 1:
            r = req(rng); ids.append(r)
            subject = f"Request {r}: {report}"
            body = (f"Hello,\n\nI'm opening request {r}. Please pull the {report} for {period} "
                    f"and share it with me {phrase}. Breakdown by cost center would be great.")
        else:
            subject = f"Need {report}"
            body = (f"Hi,\n\nLeadership is asking for the latest {report} ({period}) for {bu}. "
                    f"Can you prepare it {phrase}? It's going into the {mtg}.")
        tasks.append(f"Send the {period} {report}")

    elif category == "Data Correction":
        report, c, a1, a2 = rng.choice(REPORTS), cc(rng), money(rng), money(rng)
        ids.append(c); amounts += [a1, a2]
        variant = rng.randint(0, 2)
        if variant == 0:
            subject = f"Wrong value in {report}"
            body = (f"Hi,\n\nThe {report} shows {a1} for cost center {c}, but our ledger says it "
                    f"should be {a2}. Can you correct it {phrase}?")
        elif variant == 1:
            subject = f"Data issue - {c}"
            body = (f"Hello team,\n\nI found a discrepancy in the {report}: {c} is showing {a1} "
                    f"instead of {a2}. Please fix the data and refresh the report {phrase}.")
        else:
            subject = f"Correction needed: {report}"
            body = (f"Hi,\n\nLooks like the mapping for {c} is off. The {report} has {a1} but "
                    f"finance closed the month at {a2}. Please update it {phrase}.")
        tasks.append(f"Correct the value for {c} in the {report}")

    elif category == "Access Request":
        system = rng.choice(SYSTEMS)
        who = rng.choice(["me", "my new analyst", "our intern", "the audit team"])
        variant = rng.randint(0, 1)
        if variant == 0:
            subject = f"Access to {system} dashboard"
            body = (f"Hi,\n\nCould you please grant {who} access to the {system} dashboard? "
                    f"We need it {phrase}.")
        else:
            r = req(rng); ids.append(r)
            subject = f"{r} - access request"
            body = (f"Hello,\n\nI submitted {r} to get {who} read access to the {system} workspace. "
                    f"Please approve and set it up {phrase}.")
        tasks.append(f"Grant access to the {system} dashboard")

    elif category == "Approval Request":
        p, a, vendor = po(rng), money(rng), rng.choice(VENDORS)
        ids.append(p); amounts.append(a)
        variant = rng.randint(0, 2)
        if variant == 0:
            subject = f"Approval needed: {p}"
            body = (f"Hi,\n\nPlease review and approve {p} for {a} from {vendor} {phrase}. "
                    f"The quote is attached.")
        elif variant == 1:
            c = cc(rng); ids.append(c)
            subject = f"{vendor} invoice approval"
            body = (f"Hello,\n\nThe {vendor} invoice under {p} ({a}) is charged to {c} and needs "
                    f"your sign-off {phrase} so we don't miss the payment run.")
        else:
            subject = f"Budget approval for {vendor}"
            body = (f"Hi team,\n\nWe need approval on {p}, total {a}, for services from {vendor}. "
                    f"Can you approve it {phrase}?")
        tasks.append(f"Approve {p}")

    elif category == "Ad-hoc Analysis":
        metric, period = rng.choice(METRICS), rng.choice(PERIODS)
        pct = rng.randint(4, 35)
        variant = rng.randint(0, 2)
        if variant == 0:
            subject = f"Why did {metric} jump?"
            body = (f"Hi,\n\nCan you analyze why {metric} came in {pct}% above forecast in {period}? "
                    f"A short summary of the main drivers {phrase} would help.")
        elif variant == 1:
            a = money(rng); amounts.append(a)
            subject = f"Deep dive on {metric}"
            body = (f"Hello,\n\nWe're seeing a {a} gap in {metric} versus plan for {period}. "
                    f"Please dig into the root causes and send me your findings {phrase}.")
        else:
            subject = f"Quick analysis: {metric} trend"
            body = (f"Hi team,\n\nCould you put together a trend of {metric} for the last 6 months "
                    f"and explain the {pct}% variance in {period}? Need it {phrase}.")
        tasks.append(f"Analyze the {metric} variance for {period}")

    elif category == "Meeting Request":
        topic = rng.choice(TOPICS)
        variant = rng.randint(0, 1)
        if variant == 0:
            subject = f"Meeting to review {topic}"
            body = (f"Hi,\n\nCan we set up 30 minutes to walk through {topic}? Please send an "
                    f"invite {phrase}.")
        else:
            subject = f"Sync on {topic}"
            body = (f"Hello team,\n\nI'd like to schedule a quick sync about {topic} with you and "
                    f"{rng.choice(TEAM_MEMBERS)}. Could you find a slot and book it {phrase}?")
        tasks.append(f"Schedule a meeting about {topic}")

    else:  # FYI / No Action
        system = rng.choice(SYSTEM_DOWN)
        variant = rng.randint(0, 2)
        due = ""
        if variant == 0:
            subject = f"FYI: {system} maintenance"
            body = (f"Hi all,\n\nJust a heads-up: {system} will be down for maintenance this "
                    f"Saturday night. No action needed from your side.")
        elif variant == 1:
            subject = "Q4 calendar published"
            body = ("Hello team,\n\nFor your information, the Q4 close calendar has been published "
                    "on the finance SharePoint. Nothing to do for now.")
        else:
            topic = rng.choice(TOPICS)
            subject = f"Update on {topic}"
            body = (f"Hi,\n\nSharing a quick update: {topic} was approved by leadership yesterday. "
                    f"No action required, just keeping you in the loop.")

    return subject, body, urgency, due, amounts, ids, tasks


def make_dataset(n, seed):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        category = CATEGORIES[i % len(CATEGORIES)]
        subject, body, urgency, due, amounts, ids, tasks = build_email(category, rng)
        name, role = rng.choice(PEOPLE)
        email_addr = name.lower().replace(" ", ".") + "@example.com"
        header = f"From: {name} <{email_addr}>\nSubject: {subject}\n\n" if rng.random() < 0.7 \
            else f"Subject: {subject}\n\n"
        closing = rng.choice(["Thanks,", "Thank you,", "Best,", "Regards,"])
        text = f"{header}{body}\n\n{closing}\n{name}\n{role}"
        rows.append({
            "email_id": f"E{i + 1:04d}",
            "email_text": text,
            "category": category,
            "urgency": urgency,
            "requester": name,
            "due_date": due,
            "amounts": ";".join(amounts),
            "ids": ";".join(ids),
            "tasks": ";".join(tasks),
        })
    rng.shuffle(rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=140)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=os.path.join("data", "emails.csv"))
    args = parser.parse_args()

    rows = make_dataset(args.n, args.seed)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} emails to {args.out}")


if __name__ == "__main__":
    main()
