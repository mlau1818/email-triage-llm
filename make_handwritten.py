"""
Writes data/emails_handwritten.csv: 21 hand-written emails (3 per category) with
less regular wording than the synthetic set, used as a harder test set.
"""
import csv
import os

ROWS = [
    # Report Request
    ("Hey, do you have the latest headcount numbers for A&T? Boss wants them before tomorrow morning. Thx\n\nDan",
     "Report Request", "High", "Dan", "tomorrow morning", "", ""),
    ("From: Grace Liu <grace.liu@example.com>\nSubject: monthly pack\n\nHi! When you have a moment could you share the October opex pack? Planning to look at it end of month.\n\nCheers,\nGrace Liu",
     "Report Request", "Low", "Grace Liu", "end of month", "", ""),
    ("Subject: REQ-55821 capex view\n\nTeam - per REQ-55821 please send the capex by project view, needed by Thursday for the review.\n\nRegards,\nMark Davis\nFinance",
     "Report Request", "Medium", "Mark Davis", "Thursday", "", "REQ-55821"),
    # Data Correction
    ("From: Rita Gomez <rita.gomez@example.com>\nSubject: numbers don't tie\n\nThe dashboard has CC-3301 at $48K but SAP says $41K. Something is off, can someone take a look by Friday?\n\nThanks,\nRita Gomez",
     "Data Correction", "Medium", "Rita Gomez", "Friday", "$48K;$41K", "CC-3301"),
    ("Subject: wrong mapping!!\n\nThis needs fixing ASAP - the freight line is booked to CC-7720 instead of CC-7721 and the CFO sees it in an hour.\n\nBest,\nTom Reyes",
     "Data Correction", "High", "Tom Reyes", "ASAP", "", "CC-7720;CC-7721"),
    ("Hi, small thing - the September aging report double counts one supplier. Not urgent, sometime next week is fine.\n\nThank you,\nIrene Park",
     "Data Correction", "Low", "Irene Park", "next week", "", ""),
    # Access Request
    ("From: Ben Ortiz <ben.ortiz@example.com>\nSubject: access pls\n\nI can't open the Snowflake finance schema, getting permission denied. Can you add me today? Close starts tomorrow.\n\nThanks,\nBen Ortiz",
     "Access Request", "High", "Ben Ortiz", "today", "", ""),
    ("Subject: new hire\n\nOur new analyst Paula starts Monday. Could you set her up on the Power BI workspace by Monday?\n\nBest,\nLaura Fields\nManager",
     "Access Request", "Medium", "Laura Fields", "Monday", "", ""),
    ("From: Sam Wu <sam.wu@example.com>\nSubject: read-only SharePoint\n\nWhenever you get a chance, the auditors would like read-only rights to the 2025 folder.\n\nRegards,\nSam Wu",
     "Access Request", "Low", "Sam Wu", "", "", ""),
    # Approval Request
    ("Subject: sign-off PO-771204\n\nNeed your OK on PO-771204 ($18,400.00) for the HVAC repair, vendor won't start until it's approved. EOD today please!\n\nKaren Hill",
     "Approval Request", "High", "Karen Hill", "EOD today", "$18,400.00", "PO-771204"),
    ("From: Victor Chan <victor.chan@example.com>\nSubject: training budget\n\nCan you approve $3.5K for the team's Excel training? It's on PO-660031, by Nov 21 would be ideal.\n\nThanks,\nVictor Chan",
     "Approval Request", "Medium", "Victor Chan", "Nov 21", "$3.5K", "PO-660031"),
    ("Subject: renewal\n\nThe software renewal (PO-512900, $92K) is due at end of quarter, please approve when you can.\n\nBest regards,\nNadia Ali",
     "Approval Request", "Low", "Nadia Ali", "end of quarter", "$92K", "PO-512900"),
    # Ad-hoc Analysis
    ("From: Peter Novak <peter.novak@example.com>\nSubject: utilities???\n\nUtilities are $210K over plan this month. What's driving it? Need a view in 2 hours for the exec call.\n\nPeter Novak",
     "Ad-hoc Analysis", "High", "Peter Novak", "in 2 hours", "$210K", ""),
    ("Hi team, could someone break down the overtime trend by department and tell me why Fab is up 18%? By Wednesday works.\n\nThanks,\nJulia Stone",
     "Ad-hoc Analysis", "Medium", "Julia Stone", "Wednesday", "", ""),
    ("Subject: idea\n\nOut of curiosity, would be nice to see how scrap cost correlates with volume over the last 2 years. No rush at all.\n\nBest,\nOmar Farouk",
     "Ad-hoc Analysis", "Low", "Omar Farouk", "", "", ""),
    # Meeting Request
    ("From: Chloe Martin <chloe.martin@example.com>\nSubject: quick call?\n\nCan we jump on a call today to go over the forecast changes? 15 min is enough.\n\nThanks,\nChloe Martin",
     "Meeting Request", "High", "Chloe Martin", "today", "", ""),
    ("Subject: dashboard walkthrough\n\nI'd love a walkthrough of the new spending dashboard. Could you book something by end of week?\n\nRegards,\nGeorge Patel",
     "Meeting Request", "Medium", "George Patel", "end of week", "", ""),
    ("Hi, let's find time next week to brainstorm the 2027 reporting roadmap.\n\nCheers,\nMia Johansson",
     "Meeting Request", "Low", "Mia Johansson", "next week", "", ""),
    # FYI / No Action
    ("From: IT Service Desk <it.desk@example.com>\nSubject: planned outage\n\nPlease note the VPN will be unavailable Sunday 2-4 AM for upgrades. No action required.\n\nRegards,\nIT Service Desk",
     "FYI / No Action", "Low", "IT Service Desk", "", "", ""),
    ("Subject: congrats\n\nJust wanted to share that the audit closed with zero findings. Great work everyone!\n\nBest,\nRobert King\nController",
     "FYI / No Action", "Low", "Robert King", "", "", ""),
    ("For awareness: the exchange rate table for November has been loaded in SAP. Nothing needed from you.\n\nThanks,\nElena Petrova",
     "FYI / No Action", "Low", "Elena Petrova", "", "", ""),
]


def main(out=os.path.join("data", "emails_handwritten.csv")):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["email_id", "email_text", "category", "urgency", "requester",
                    "due_date", "amounts", "ids"])
        for i, r in enumerate(ROWS, 1):
            w.writerow([f"H{i:03d}", *r])
    print(f"Wrote {len(ROWS)} emails to {out}")


if __name__ == "__main__":
    main()
