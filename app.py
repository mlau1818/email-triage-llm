"""
Gradio interface for the email triage + extraction system.

Usage:
    python src/app.py            # local: open http://127.0.0.1:7860
    python src/app.py --share    # public link (use this in Google Colab)
"""
import argparse
import os
import tempfile

import gradio as gr
import pandas as pd

from triage import EmailTriage, sort_by_urgency

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_PATH = os.path.join(ROOT, "data", "emails_handwritten.csv")
URGENCY_BADGE = {"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🟢 Low"}

print("Loading models (first run downloads them, ~2 GB)...")
TRIAGE = EmailTriage(urgency_mode="hybrid")
SAMPLES = pd.read_csv(SAMPLE_PATH).fillna("")


def fmt_list(values):
    return ", ".join(values) if values else "—"


def analyze_email(text):
    if not text or not text.strip():
        raise gr.Error("Paste an email first.")
    r = TRIAGE.triage(text)
    urgency_md = (f"## {URGENCY_BADGE[r['urgency']]}\n"
                  f"*Decided by: {r['urgency_source']}* "
                  f"(model alone would say **{r['urgency_model']}**)")
    tasks_md = "\n".join(f"- [ ] {t}" for t in r["tasks"]) or "_No action requested._"
    fields = pd.DataFrame({
        "Field": ["Requester", "Due date", "Amounts", "Reference IDs"],
        "Value": [r["requester"] or "—", r["due_date"] or "—",
                  fmt_list(r["amounts"]), fmt_list(r["ids"])],
    })
    return r["category_scores"], urgency_md, r["summary"], tasks_md, fields


def analyze_inbox(file):
    df = pd.read_csv(file.name if hasattr(file, "name") else file) if file is not None \
        else SAMPLES.copy()
    if "email_text" not in df.columns:
        raise gr.Error("The CSV needs a column called 'email_text'.")
    df = df.fillna("")
    results = TRIAGE.triage_batch(df["email_text"].tolist())
    rows = []
    for i in sort_by_urgency(results):
        r = results[i]
        rows.append({
            "Urgency": URGENCY_BADGE[r["urgency"]],
            "Category": r["category"],
            "Requester": r["requester"],
            "Due": r["due_date"],
            "Summary": r["summary"],
            "Tasks": "; ".join(r["tasks"]),
            "Amounts": "; ".join(r["amounts"]),
            "IDs": "; ".join(r["ids"]),
        })
    table = pd.DataFrame(rows)
    counts = table["Category"].value_counts()
    summary_md = (f"**{len(table)} emails** · "
                  f"{(table['Urgency'] == URGENCY_BADGE['High']).sum()} high urgency · "
                  + " · ".join(f"{c}: {n}" for c, n in counts.items()))
    out_path = os.path.join(tempfile.gettempdir(), "triaged_inbox.csv")
    table.to_csv(out_path, index=False)
    return summary_md, table, out_path


def load_sample(choice):
    idx = int(choice.split(" ")[0]) - 1
    return SAMPLES.loc[idx, "email_text"]


with gr.Blocks(title="Email Triage") as demo:
    gr.Markdown("# 📬 Email Triage + Extraction\n"
                "Classifies finance/data team requests, sets urgency and pulls out the "
                "key fields. Models: `bart-large-mnli` (zero-shot) + `flan-t5-base`.")

    with gr.Tab("Single email"):
        with gr.Row():
            with gr.Column(scale=1):
                sample_dd = gr.Dropdown(
                    choices=[f"{i + 1} - {t.splitlines()[0][:60]}"
                             for i, t in enumerate(SAMPLES["email_text"])],
                    label="Load an example")
                email_in = gr.Textbox(lines=14, label="Email",
                                      placeholder="Paste the email here (From/Subject optional)")
                run_btn = gr.Button("Analyze", variant="primary")
            with gr.Column(scale=1):
                urgency_out = gr.Markdown()
                category_out = gr.Label(num_top_classes=3, label="Category")
                summary_out = gr.Textbox(label="Summary", lines=2)
                tasks_out = gr.Markdown(label="Tasks")
                fields_out = gr.Dataframe(label="Extracted fields", interactive=False)
        sample_dd.change(load_sample, sample_dd, email_in)
        run_btn.click(analyze_email, email_in,
                      [category_out, urgency_out, summary_out, tasks_out, fields_out])

    with gr.Tab("Inbox (CSV)"):
        gr.Markdown("Upload a CSV with an `email_text` column, or leave it empty to use the "
                    "21 example emails. Results come back sorted by urgency.")
        file_in = gr.File(label="CSV file", file_types=[".csv"])
        inbox_btn = gr.Button("Triage inbox", variant="primary")
        inbox_summary = gr.Markdown()
        inbox_table = gr.Dataframe(interactive=False, wrap=True)
        inbox_file = gr.File(label="Download results")
        inbox_btn.click(analyze_inbox, file_in, [inbox_summary, inbox_table, inbox_file])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--share", action="store_true", help="create a public link (Colab)")
    args = parser.parse_args()
    demo.launch(share=args.share)
