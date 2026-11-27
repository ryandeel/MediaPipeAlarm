"""
summarize a --log CSV from alarm_app.py into one row per challenge

usage: python src/summarize_log.py results.csv

for jumping jacks, fill in the actual_reps column by hand (how many jumping
jacks the person really did before the app counted 5) and the table will
also show how accurate the rep counter was
"""

import csv
import statistics
import sys
from collections import defaultdict


def summarize(rows):
    by_challenge = defaultdict(list)
    for row in rows:
        by_challenge[row["challenge"]].append(row)

    table = []
    for challenge, runs in sorted(by_challenge.items()):
        done = [r for r in runs if r["result"] == "completed"]
        times = [float(r["seconds_to_finish"]) for r in done if r["seconds_to_finish"]]
        seen = [float(r["person_detected_pct"]) for r in runs if r["person_detected_pct"]]

        # rep accuracy: compare what the app counted with what the person really did
        rep_runs = [r for r in done if r["reps_counted"] and r["actual_reps"].strip()]
        if rep_runs:
            exact = sum(int(r["reps_counted"]) == int(r["actual_reps"]) for r in rep_runs)
            off_by = statistics.mean(abs(int(r["reps_counted"]) - int(r["actual_reps"])) for r in rep_runs)
            reps = f"{exact}/{len(rep_runs)} exact, avg off by {off_by:.1f}"
        else:
            reps = "-"

        table.append([
            challenge,
            str(len(runs)),
            f"{len(done)} ({100 * len(done) / len(runs):.0f}%)",
            f"{statistics.median(times):.1f}" if times else "-",
            f"{statistics.mean(seen):.0f}%" if seen else "-",
            reps,
        ])
    return table


def print_table(table):
    header = ["Challenge", "Runs", "Completed", "Median seconds to finish",
              "Person detected", "Rep count accuracy"]
    widths = [max(len(str(x)) for x in col) for col in zip(header, *table)]
    line = lambda cells: "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"
    print(line(header))
    print("|" + "|".join("-" * (w + 2) for w in widths) + "|")
    for row in table:
        print(line(row))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("No runs in this file yet.")
        return
    print_table(summarize(rows))


if __name__ == "__main__":
    main()
