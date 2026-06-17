import argparse
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

TASK_TYPES = {"clicks", "carts", "orders"}

def iter_sessions(path, max_sessions=None):
    with Path(path).open("r", encoding="utf-8") as f:
        for index, line in enumerate(f):
            if max_sessions is not None and index >=max_sessions:
                break
            if line.strip():
                yield json.loads(line)


def count_popular(train_path, pool, max_sessions=None):
    counts = Counter()
    for session in iter_sessions(train_path, max_sessions=max_sessions):
        for event in session["events"]:
            counts[event["aid"]] += 1
    
    return [aid for aid, _ in counts.most_common(pool)]

def iter_pairs(events, n_trunc, time_window):
    #循环遍历list，应该是维护下标指针
    #window为一个新的list，event[-n_trunc:]的index转移到0开始
    window = events[-n_trunc:]
    for i in range(len(window)):
        #range(a, b)为左闭右开
        for j in range(i+1, len(window)):
            a, b = window[i], window[j]
            if a["aid"] == b["aid"]:
                continue
            if abs(a["ts"]-b["ts"]) > time_window:
                continue
            yield a["aid"], b["aid"]
    



#covis矩阵
def build_covis(train_path, n_trunc, time_window, top_neighbors, max_sessions=None):
    covis = defaultdict(Counter)
    for session in iter_sessions(train_path, max_sessions=max_sessions):
        #带有iter的function应该要使用yield进行逐条返回
        for a, b in iter_pairs(session["events"], n_trunc, time_window):
            covis[a][b] += 1
            covis[b][a] += 1
            #convis [x]会创建一个key为x，value为counter的一个字典，
            #convis [x][y],操作的是counter-->counter[y]+=1
        
    pruned = {}
    for a, counter in covis.items():
        pruned[a] = dict(counter.most_common(top_neighbors))
        #{aid: {neighbor: score}} 
    return pruned

def predict_covis(events, covis, popular_list, n_recent, k):
    scores = Counter()
    aids = [e["aid"] for e in events[-n_recent:]]
    for q in aids:
        for neighbor, s in covis.get(q, {}).items():
            scores[neighbor] += s
    ranked = [aid for aid, _ in scores.most_common()]

    for popular_aid in popular_list:
        if len(ranked) >= k:
            ranked = ranked[:k]
            break
        if popular_aid not in ranked:
            ranked.append(popular_aid)

    return ranked
        



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="projects/otto-session-recsys/data/processed/local_train.jsonl")
    parser.add_argument("--test", default="projects/otto-session-recsys/data/processed/local_val_input.jsonl")
    parser.add_argument("--output", default="projects/otto-session-recsys/src/eval/pred_covisitation.csv")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--n-trunc", type=int, default=30)
    parser.add_argument("--time-window", type=int, default=60 * 60 * 1000)
    parser.add_argument("--top-neighbors", type=int, default=40)
    parser.add_argument("--n-recent", type=int, default=20, help="预测时用输入段最后N个item查询")
    parser.add_argument("--max-sessions", type=int, default=None)
    args = parser.parse_args()

    print("building co-visitation matrix (from local_train) ...")
    covis = build_covis(args.train, args.n_trunc, args.time_window, args.top_neighbors, args.max_sessions)
    print(f"    covis size:{len(covis)} items")

    print("counting popular pool for backfill (from local_train) ...")
    popular_list = count_popular(args.train, pool=max(args.top_k * 5, 100), max_sessions=args.max_sessions)
    
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["session_type", "labels"])
        for session in iter_sessions(args.test, args.max_sessions):
            sid = session["session"]
            preds = predict_covis(session["events"], covis, popular_list, args.n_recent, args.top_k)
            labels = " ".join(str(aid) for aid in preds)
            for task_type in TASK_TYPES:
                writer.writerow([f"{sid}_{task_type}", labels])
            n += 1
    print(f"wrote {args.output} ({n} sessions)")

if __name__ == "__main__":
    main()
