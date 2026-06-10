# reviewer_outputs/

Committed provenance for **live** LLM reviewer/pick runs (Rules 1 & 13).

Each `<run_id>.jsonl` holds one row per candidate: the exact prompt, the model's
full raw response, the returned model snapshot, the decision, and the input
context. The matcher run's D1 output node records the file path + content sha256,
so the recorded hash is verifiable against the file and the decision is replayable.

Offline tests write to a pytest `tmp_path` instead, so this directory holds only
real, committed runs.
