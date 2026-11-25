# Final Kaggle submission gate

The current local commit is a development checkpoint only. Complete these items before submission:

- [ ] Create a public GitHub repository (suggested name: `NORTHSTAR-PLE`) under your account and push this Git repository.
- [ ] Ensure the exact public commit contains `submission.yaml`, `serve.py`, `harness.py`, MIT `LICENSE`, and official unpacked `artifacts/`.
- [ ] Obtain gated dev-set access; configure HF read access and a model proxy using your own credentials (never commit tokens or `.env`).
- [ ] Run the official PLE kit check with cancellation test; fix all failures.
- [ ] Run official `eval/run.py` on all 29 dev tasks. Save the resulting artifact directory from the official runner only.
- [ ] Run `kit artifacts` and offline artifact regrade. Confirm file-count/size rules and artifact manifest commit consistency.
- [ ] Record scores, costs, tokens, run time, tool calls, failures and repeat variability from actual evaluation outputs. Fill CSVs and regenerate plots.
- [ ] Conduct controlled cross-model and verification-loop experiments; document actual model/judge configuration.
- [ ] Replace the writeup's repository URL and commit placeholder with the pushed public URL and exact 40-character commit SHA.
- [ ] Upload `media/cover.jpg` to Kaggle Media Gallery as cover. Attach architecture, score-vs-cost, and dev failure breakdown figures.
- [ ] Review the final writeup is <=2,000 words, covers all 5 criteria, has working links, and contains no unsupported claims.
- [ ] Submit the Kaggle Writeup (not draft). Confirm the page shows submitted status.

## Local official runner

```bash
PLE_REPO=/path/to/google-research-ple \
  bash scripts/run_official_validation.sh
```

Do not mark the gate complete based on local mock tests.
