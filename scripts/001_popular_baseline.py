import csv
import json
import  argparse
from collections import Counter, defaultdict
from pathlib import Path


TASK_TYPES = {"clicks","carts","orders"}

#流式数据读取
def iter_sessions(path, max_sessions=None):
    with Path(path).open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):#读取的josnl文件，每行都是一个完整的issue：session ：n*(aid,ts,type)
            if max_sessions is not None and idx >= max_sessions:
                break
            if line.strip():
                yield json.loads(line)#与return 不同，外部要数据时，返回一次

#训练
def count_popular_items(path, event_types, max_sessions=None):
    event_types = set (event_types)
    counts = Counter()
    for session in iter_sessions(path, max_sessions=max_sessions):
        for event in session["events"]:
            if  event["type"] in event_types:
                counts[event["aid"]]+=1
    return counts      

#返回商品和次数，只要商品的名称（训练结果）
def get_top_items(counts, k):
    return [aid for aid, _ in counts.most_common(k)]

#评价
def evaluate_leave_last(train_path, labels_by_type, max_sessons=None):
    hits = defaultdict(int)
    totals = defaultdict(int)
    
    for session in iter_sessions(train_path, max_sessions=max_sessons):
        events = session["events"]
        if len(events) < 2:
            continue

        target = events[-1]
        target_type = target["type"]
        target_aid = target["aid"]
        if target_type not in TASK_TYPES:
            continue

        totals[target_type] += 1
        if target_aid in labels_by_type[target_type]:
            hits[target_type] += 1

    for task_type in TASK_TYPES:
        total = totals[task_type]
        recall = hits[task_type] / total if total else 0.0
        print(f"{task_type}: recall@20={recall:.6f} ({hits[task_type]}/{total})")
    
    total_hits = sum(hits.values())
    total_count = sum(totals.values())
    overall = total_hits / total_count if total_count else 0.0
    print(f"overall :recall@20={overall:.6f} ({total_hits}/{total_count})")


def write_submission(test_path, output_path, labels_by_type, max_sessions=None):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["session_type", "labels"])
        for session in iter_sessions(test_path, max_sessions=max_sessions):
            session_id = session["session"]
            for task_type in TASK_TYPES:
                labels = " ".join(str(aid) for aid in labels_by_type[task_type])
                writer.writerow([f"{session_id}_{task_type}", labels])

def parse_event_types(raw):
    if raw == "per_type":
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]
          

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="projects/otto-session-recsys/data/raw/otto-recsys-train.jsonl")
    parser.add_argument("--test", default="projects/otto-session-recsys/data/raw/otto-recsys-test.jsonl")
    parser.add_argument("--output", default="projects/otto-session-recsys/scripts/popular_submission.csv")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--max-sessions", type=int, default=None)
    parser.add_argument(
        "--popular-by",
        default="orders",
        help="Use comma-separated event types, e.g. orders or clicks,carts,orders. Use per_type for one top list per task.",
    )
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()

    popular_by = parse_event_types(args.popular_by)

    if popular_by is None:
        labels_by_type = {}
        for task_type in TASK_TYPES:
            counts = count_popular_items(args.train, [task_type], args.max_sessions)
            labels_by_type[task_type] = get_top_items(counts, args.top_k)
            print(f"{task_type} top-{args.top_k}: {labels_by_type[task_type]}")
    else:
        counts = count_popular_items(args.train, popular_by, args.max_sessions)
        labels = get_top_items(counts, args.top_k)
        labels_by_type = {task_type: labels for task_type in TASK_TYPES}
        print(f"global top-{args.top_k} by {popular_by}: {labels}")

    if args.eval:
        evaluate_leave_last(args.train, labels_by_type, args.max_sessions)

    write_submission(args.test, args.output, labels_by_type, args.max_sessions)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()

    

            