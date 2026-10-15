# Protocol v2.0 runs of reviewer B and the reconciler (withdrawn, 2026-10-15)

Kept for the record (Rule 13); they decide nothing.

- **The parser.** v2.0 accepted only a bare JSON object at the end of the answer. Reviewer B
  and the reconciler (claude-opus-5-5) often wrapped it in a closing ```json fence. Such a
  call was stored and retried. After the reconciler fenced three of three attempts on one unit
  the retry cap was raised to 6; it then fenced six of six on another, so the run could not
  finish.
- **Why not re-read.** Reading these stored attempts under a fence-tolerant parser would have
  changed two of B's answers, Neferuni and Meryetyotes. On both, an earlier fenced attempt
  answered differently from the accepted bare one, and both answers had been seen.
- **What replaced them.** B and the reconciler were run afresh under v2.1 (fence-tolerant)
  instead. Reviewer A's stored calls read the same under both parsers (checked by the tests)
  and stand.
- **What the record shows.** The two changed answers are evidence of sampling variance
  within one reviewer.
