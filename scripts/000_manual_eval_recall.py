import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

TASK_TYPES = {"clicks", "carts", "orders"}
WEIGHTS = {"clicks": 0.10, "carts": 0.30, "orders": 0.60}

def load_labels(path):
    labels = {}
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            sid = obj["session"]
            labels[sid] = {t: set(obj.get(t, [])) for t in TASK_TYPES}

    return labels

def load_prediction(path):
    preds = {}
    with Path(path).open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)#跳过表头
        for row in reader:
            if not row:
                continue
            session_type, labels_str = row[0], row[1] if len(row) > 1 else ""
            sid_str, task_type = session_type.rsplit("_", 1)
            aids = [int(x) for x in labels_str.split()] if labels_str else []
            preds[(int(sid_str), task_type)] = aids
    return preds

def recall_hits_denom(pred_list, gt_set, k):
    #防止preds中出现重复标签，让recall的值出现异常值或者虚高
    hits = len(set(pred_list[:k]) & gt_set)
    denom = min(k, len(gt_set))
    return hits , denom


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", default="projects/otto-session-recsys/data/processed/local_val_labels.jsonl")
    parser.add_argument("--pred", required=True, help="submission 格式的预测文件")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    labels = load_labels(args.labels)
    #{session_id:{"click":{aids}, "carts":{}, "orders":{aids}}}
    preds = load_prediction(args.pred)
    #{(session_sid,"click"):aids}
    k = args.top_k

    sum_hits = defaultdict(int)
    sum_denom = defaultdict(int)

    for sid, gt_by_type in labels.items():
        for task_type in TASK_TYPES:
            gt = gt_by_type[task_type]
            if not gt:
                continue
            pred_list = preds.get((sid, task_type), [])
            hits, denom = recall_hits_denom(pred_list, gt, k)
            sum_hits[task_type] += hits
            sum_denom[task_type] += denom

    weighted = 0.0
    for task_type in TASK_TYPES:
        denom = sum_denom[task_type]
        recall = sum_hits[task_type] / denom if denom else 0.0
        weighted += WEIGHTS[task_type] * recall
        print(f"{task_type:>7}: recall@{k}={recall:.6f} ({sum_hits[task_type]}/{denom})")

    print(f"weighted score = {weighted:.6f} (0.1*clicks + 0.3carts + 0.6*orders)")

if __name__ == "__main__":
    main()   


        




