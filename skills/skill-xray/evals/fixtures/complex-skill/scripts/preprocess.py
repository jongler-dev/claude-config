#!/usr/bin/env python3
"""Pre-process a CSV file to extract column types and basic statistics."""

import csv
import json
import sys


def analyze_csv(csv_path, output_path):
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        result = {"error": "Empty CSV file", "columns": [], "row_count": 0}
    else:
        columns = []
        for col in rows[0].keys():
            values = [r[col] for r in rows if r[col]]
            columns.append({
                "name": col,
                "non_null_count": len(values),
                "unique_count": len(set(values)),
                "sample_values": values[:5]
            })
        result = {
            "columns": columns,
            "row_count": len(rows),
            "column_count": len(columns)
        }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <csv-path> <output-path>", file=sys.stderr)
        sys.exit(1)
    analyze_csv(sys.argv[1], sys.argv[2])
