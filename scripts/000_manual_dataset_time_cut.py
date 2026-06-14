import argparse
import json
import random
from pathlib import Path

TASK_TYPE = {"clicks", "carts", "orders"}
MS_PER_DAY = 24 * 60 * 60 *1000


#IO
def iter_sessions(path, max_sessions=None):
    with Path(path).open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if max_sessions is not None and idx >= max_sessions:
                break
            if line.strip():
                yield json.loads(line)

def find_max_ts(path, max_sessions):
    max_ts = 0
    for session in iter_sessions(path, max_sessions=max_sessions):
        for event in session["events"]:
            if event["ts"] > max_ts:
                max_ts = event["ts"]
    return max_ts
            
def write_jsonl_line(fh, obj):
    fh.write(json.dumps(obj) + "\n")


#————————————————————————核心逻辑————————————————————————————————————

def assign_split(session, split_ts):
    last_event = session["events"][-1]
    last_ts = last_event["ts"]

    return "val" if last_ts >= split_ts else "train"

def truncate_session(events, rng):
    len_events = len(events)
    k = rng.randint(1,len_events-1)
    input_events = events[:k]
    answer_events = events[k:]

    return input_events, answer_events

def extract_labels(answer_events):
    labels = {task_type : [] for task_type in TASK_TYPE}
    for event in answer_events:
        if event["type"] in TASK_TYPE:
            labels[event["type"]].append(event["aid"])
    
    labels = {task_type : list(set(labels[task_type])) for task_type in TASK_TYPE}

    return labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="projects/otto-session-recsys/data/raw/otto-recsys-train.jsonl")
    parser.add_argument("--out-dir", default="projects/otto-session-recsys/data/processed")
    parser.add_argument("--holdout-days", type=int, default=7)
    parser.add_argument("--split-ts", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-sessions", type=int, default=None)
    args = parser.parse_args()

    #确定train和val的分界
    if args.split_ts is not None:
        split_ts = args.split_ts
    else:
        print("scanning max ts")
        max_ts = find_max_ts(args.train, args.max_sessions)
        split_ts = max_ts - args.holdout_days * MS_PER_DAY
    print(f"level1 split_ts = {split_ts} (>= 改时间的 session 归 val)")

    #
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    p_train = out_dir / "local_train.jsonl"
    p_input = out_dir / "local_val_input.jsonl"
    p_labels = out_dir / "local_val_labels.jsonl"

    rng = random.Random(args.seed)
    n_train = n_val = n_skip = 0

    with p_train.open("w", encoding="utf-8") as f_train, \
         p_input.open("w", encoding="utf-8") as f_input, \
         p_labels.open("w", encoding="utf-8") as f_labels:
        
        for session in iter_sessions(args.train, args.max_sessions):
            sid = session["session"]
            events = session["events"]

            #划分非level1的训练集
            if assign_split(session, split_ts) == "train":
                write_jsonl_line(f_train, session)
                n_train += 1
                continue
            
            #
            if len(events) < 2:
                n_skip += 1
                continue

            input_events , answer_events = truncate_session(events, rng)
            labels = extract_labels(answer_events)

            write_jsonl_line(f_input, {"session": sid, "events": input_events})

            write_jsonl_line(f_labels, {"session" : sid, **labels})
            n_val += 1
        
    print(f"done. train={n_train}  val={n_val}  skipped(too short)={n_skip}")
    print(f"  -> {p_train}")
    print(f"  -> {p_input}")
    print(f"  -> {p_labels}")

    # 简单自检：两边都得有数据，否则切点或 split 逻辑有问题
    assert n_train > 0, "训练段为空：split_ts 可能太小"
    assert n_val > 0, "验证段为空：split_ts 可能太大 / holdout-days 太小"


if  __name__ == "__main__":
    main()