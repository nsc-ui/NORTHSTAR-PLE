Worked for 10m 14s

### NORTHSTAR-PLE — final development package

I've upgraded the prototype, added the missing supporting materials, tested the harness, created a Git history bundle, and packaged the project.

### Downloads

Complete project ZIP

Source code, test suite, cover image, diagrams, report, documentation and checklist

Download complete project ZIP

Git repository bundle

Preserves commit history and the exact commit SHA; tested by cloning it

Download Git bundle

### Individual submission assets

![College of Engineering — RUST](https://images.openai.com/static-rsc-4/aRbLqrmlSy-T_n4hMl0LD8odhI2BZiUPauGKcJV0ssVXX6QMf3TQJJJ80rDBdMtrkMobiBrEMukHP2EDHn09gSWp5JIU1f5HVocTfHZ1EBCXLxZdAw1GxQld1CtcOJJMYFXh4KvGF_7iT-LYq6pGtrIfO0K2q5KZMm1gUz7bvhLziAOPfZtS6yyPM_9wMThG?purpose=fullsize)

Kaggle cover image

Download cover image

Ready to upload to the Kaggle Media Gallery.

* Stage 1 writeup draft (795 words)

* Architecture diagram

* Score-versus-cost figure

* Failure breakdown figure

* Local test report

* Official submission checklist

### What changed in the harness

NORTHSTAR is now significantly more capable than the original starter.

* Adaptive context management: compresses older task history into a progress ledger while preserving the original instructions, decisions, evidence, calculations, and recent tool interactions.

* Engineering verification: explicit requirements matrix, evidence ledger, dimensional checks, independent validation, skeptical review and repair.

* MCP improvements: concurrent discovery, catalog pagination, searchable tool schemas, session reuse and JSON/SSE parsing.

* More robust execution: transient-error retries, bounded backoff, tool-error recovery, 110-turn limit, longer model response timeout and cancellation handling.

* Final audit tool: checks workspace contents, empty files, compilation and available validators.

* Safer logging: does not log raw tool arguments or task contents.

* Time management: reserves time for final deliverable verification rather than running until the deadline.

The configured model is `google-cloud/gemini-4-neon`. The public PLE leaderboard currently lists a Gemini 4 Neon agent configuration among its leading results, but that is not a NORTHSTAR benchmark result; we still need to test our actual harness. Mercor +1

### Tests completed

| Validation                        | Result     |
| --------------------------------- | ---------- |
| Python compilation                | PASS       |
| Local entry checks                | 15/15 PASS |
| MCP unit tests                    | PASS       |
| Context compaction test           | PASS       |
| Cancellation test                 | PASS       |
| Mock WebSocket smoke test         | PASS       |
| ZIP integrity and required files  | PASS       |
| Git bundle verification and clone | PASS       |

The mock smoke test successfully executed a tool call, returned protocol results, performed its final verification turn, and sent the completion message.

These are software/harness tests—not engineering benchmark scores.

### Minimum requirements — current status

I have prepared the materials, but the competition's actual qualification gate is not yet passed.

Prepared

1\. Writeup and project materials

The 795-word writeup covers all five judging criteria, with the cover and architecture figure prepared. The two performance figures still need genuine dev-set data, and the Kaggle writeup has not been submitted.

Incomplete

2\. GitHub repository and commit

The local repository is committed. However, I could not create a public GitHub repository through the available connected GitHub tools, and there is no public project URL yet.

Configured

3\. Google-sponsored model

`submission.yaml` is configured to use `google-cloud/gemini-4-neon`. The exact Stage 2 accepted-model list should be confirmed before submission.

Blocked

4\. Official kit, artifacts and evaluation

The official evaluation environment isn't available here. Docker isn't installed, the official kit is absent, and gated dataset access/model proxy credentials aren't configured.

The official benchmark requires running the 29-task development set, generating the real unpacked `artifacts/` directory, and passing the official kit and artifact checks. The dev set is gated and the evaluation environment requires Docker. GitHub +2

I deliberately did not create fake artifacts or invent scores. That would risk disqualifying the submission.

### Current commit

Final development commit SHA (40 characters)

6e3e32a1dee728e2361b1db0fda804342c0ff9d9

Copy SHA

This commit is the current development version, not yet a valid competition submission commit, because it does not contain official evaluation artifacts.

### What is needed to finish the actual competition submission

* Create the public GitHub repository and push the Git bundle.

* Run the official PLE evaluation in a Docker-enabled environment with authorized dataset access and a configured model proxy.

* Generate the real 29-task artifacts and measurements.

* Replace the placeholder score-cost and failure plots with measured data.

* Finalize the writeup, attach the cover and figures, and submit it on Kaggle.

Your PLE update/deadline monitor is already set up from our earlier step.

The project is now ready for the official evaluation stage. The remaining blockers are the benchmark environment, dataset access, GitHub publication and Kaggle submission—not the starter code. Once you have the Docker-enabled evaluation environment and dataset access, I can help carry the official run through to the measured artifacts and final writeup.
