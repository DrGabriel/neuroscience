# Pre-specification draft: three reanalyses of the open data requested by the referees (round 3)

Draft of 21 October 2026, for the authors to review, commit and then paste into the paper as Appendix E.15 before any
of the three reanalyses is run. None of them has been run on real data. Their code (`analysis/open_data/`:
`snr_matching.py`, `snr_simulation.py`, `snr_control.py`, `monkey_bootstrap.py`, `reseeded.py`, `launch_reseeded.py`
and `round3_settings.py`) was proved on synthetic data only, with unit tests whose answers are known and end-to-end runs
of every command on synthetic files. No recording was opened. From the result files of 21 October only derived values
were read while the code was written: the per-subject run times (`seconds`), to estimate run times and order the
Michigan subjects; the number of trials per PRIOS connection (median 10, range 6 to 11), to choose the trial counts of
the simulation; and the monkey, agent and session labels of the Neurotycho files, to fix the resampling structure.
While the SNR control was being written, the committed latency estimator was also run on synthetic responses, about
20 synthetic connections per condition, to check the code; what that check showed is stated in E.15.2, because it
shaped the simulation and the expectations. The committed code, `deviations.py` and `exploratory_group.py` are
unchanged. The runs are to be launched by the lead author only after the code and this text are committed.

---

### E.15 Reanalyses requested by the referees after the results of E.14

#### E.15.1 Status and common rules

The referees asked for three reanalyses after the results of E.14 had been seen by them and by us. Each is therefore
exploratory: it was fixed, and committed with its code, after E.14 and before its own run, and none of them changes a
verdict of E.14. Their results are reported beside those of E.14, never in their place.

- **Seed.** Every random step uses the committed seed, 20261021 (`settings.SEED`), as stated below for each.
- **Numbers.** Every number on which a reanalysis depends that is not already in `settings.py` is in
  `analysis/open_data/round3_settings.py`.
- **Provenance.** Every result file records, as before, the commit, the SHA-256 of every analysis module, every
  setting and the software versions. The settings of this round are written into each of its result files.
- **Inputs.** R1 reads the PRIOS recordings again and R3 the Michigan recordings; R2 reads only the per-session
  result files of 21 October.

#### E.15.2 R1: H5a with a signal-to-noise control (PRIOS)

**Concern.** Lower evoked amplitude under propofol could by itself make single-trial latency estimates noisier, and so
inflate the trial-to-trial spread on which H5a rests (E.9 stated this confound).

**What was seen before this was fixed.** The H5a results of E.14 (exploratory: median $r$ 1.28 over six patients,
p 0.031). No signal-to-noise ratio (SNR) of the data has been computed or read. While the code was being written, the
committed estimator was run on synthetic responses (10 trials, a 2 ms true jitter, white noise). It showed that when
each trial is aligned with a template that includes that trial, a low SNR pulls the single-trial shifts towards zero,
because each trial then aligns best with its own noise at zero shift: below an SNR of about 6 the measured spread fell
far below the true 2 ms instead of rising above it. With 200 trials per state the same estimator behaved as the
referees expect, a lower SNR raising the spread. This is why the simulation below varies the number of trials and
includes a null check of the matching.

**Data and connections.** The exploratory H5a analysis exactly as run for E.14: the committed code, the same seed and
therefore the same connections and the same equalised trials, with deviation D4 for sub-PRIOS02. The H5a statistic is
recomputed alongside; it must reproduce E.14 (median $r$ 1.28, p 0.031). If it does not, the reanalysis is stopped
and the discrepancy reported.

**SNR of a connection in one state.** On the baseline-corrected, equalised trials of H5a: the absolute value of the
mean response at its N1 (the committed peak: the largest negative deflection from 9 to 100 ms), divided by the noise,
the median over trials of the standard deviation of the de-meaned first 266 samples of the trial (from −500 to
−370 ms at 2,048 Hz). 266 samples is the length of the span the latency estimator reads (about −11 to 119 ms around the
pulse), so the noise is measured over the same length as it acts.

**(a) Matching rule.** For each connection, the state with the higher SNR is degraded to the SNR of the other. Each of
its trials receives, over the span the estimator reads only, the de-meaned first 266 samples of the next trial of the
same state (the last trial receives the first trial's), multiplied by $\sqrt{(\text{SNR}_\text{high}/\text{SNR}_\text{low})^2 - 1}$,
which raises the noise of that state by the factor that equalises the two SNRs. The added noise is the state's own
pre-pulse activity, so it has that state's spectrum, and no random draw is involved. Mean latency, single-trial
latencies and their spread are then measured on the degraded trials by the committed estimator
(`evoked_latency.connection_latency`, as `pipeline_prios.measure` calls it), and the matched relative change
$r_\text{matched} = \log(\text{SD}_\text{prop}/\text{SD}_\text{awake}) - \log(\text{latency}_\text{prop}/\text{latency}_\text{awake})$
is computed as in H5a. A connection whose matched spread is zero in either state has no $r_\text{matched}$. Per
patient, the median over connections. Because the SNR is taken from the mean response, a larger true jitter, which
flattens the mean response, also lowers the SNR of its state, and matching then adds noise to the other state. With
many trials this can only remove part of a true rise. At H5a's trial counts, where a lower SNR can lower the measured
spread (below), it can instead raise $r_\text{matched}$; the null check of (b) measures this.

**(a′) Restriction (secondary).** The H5a statistic as run, restricted to connections whose propofol SNR is at least
the awake SNR divided by 1.25 (log SNR ratio at least −0.22). Connections whose SNR rose under propofol are kept,
because under the referees' concern a higher SNR cannot inflate the spread; the simulation shows whether that holds at
H5a's trial counts. Per patient, the median over the kept connections; a patient with no
kept connection is left out of this row.

**(b) Simulation.** Synthetic cortico-cortical evoked potentials go through the committed H5a measure
(`pipeline_prios.measure`: baseline correction, response test, N1 latency and single-trial alignment) at 2,048 Hz over
the committed trial span (−500 to +120 ms). Each response is a negative Gaussian deflection, latency 22 ms (the awake
median of van Blooijs et al., 2024, E.1), width (standard deviation) 5 ms, an assumed shape, with a Gaussian
trial-to-trial jitter of the latency. Noise is Gaussian with unit standard deviation over each trial, white or pink
(power falling as 1/f). The grid: nominal SNR (amplitude over noise standard deviation) from 0.5 to 16 in eleven
half-octave steps; true jitter 0, 2 and 4 ms; 6 and 10 trials (the range and median of H5a's equalised trial counts)
and 100 trials (to show the large-sample behaviour); 200 synthetic connections per cell; one generator seeded with the
committed seed. Per cell: the median measured SNR (measured as for the data), the median latency spread over
connections that pass the response test, and the share that pass. From these, for every pair of SNRs within a colour,
jitter and trial count, the $r$ an SNR change alone produces, $\log$ of the spread at the lower SNR over that at the
higher (the mean latency is the same by construction). **Null check:** the matching rule itself on synthetic pairs
of states that differ only in SNR (10 trials; awake SNR 4, 8 and 16; propofol SNR half or a quarter of it; every
colour and jitter; 200 connections each), reporting the median $r$ as run and after matching. Finally, the group
step reads the simulation at the group median SNRs of the data (the median over patients of each patient's median
awake and propofol SNR), interpolating log spread in log measured SNR, and reports for each colour, jitter and trial
count the $r$ the observed SNR change alone would produce, and whether the observed SNRs lie inside the simulated
range.

**(c) Test, reported without verdict.** As H5a: one-sided Wilcoxon signed-rank test over patients of the per-patient
median $r_\text{matched}$ > 0, with its median and the SESOI $\log 1.2$, beside the same test for the H5a statistic as
run and for the restricted statistic. No verdict, as for H5a (E.9): six patients, one deep state, two days. With six
patients the smallest one-sided p-value is 1/64 = 0.016, and 0.031 if the patient closest to zero goes the other way. The reading is
fixed now. First, sensitivity: matching lowers one state's SNR, and the simulation may show that at the matched SNR
the estimator no longer sees a true jitter. The matched SNR of a connection is the lower of its two SNRs; the group
value is the median over patients of each patient's median. If, at that SNR, the simulated median spread of a 2 ms
true jitter with 10 trials (interpolated in log measured SNR) is below 1 ms in either noise colour, the matched
comparison cannot detect a rise, and its result is reported as uninformative rather than read either way. Otherwise:
if the median $r_\text{matched}$ is at least $\log 1.2$ with p below 0.05, the rise of latency variability over
latency in H5a is not explained by a difference in SNR between the states; if it falls below $\log 1.2$ while the H5a
statistic as run stays above it, the H5a result is not distinguishable from an SNR difference and will be reported as
such in Section 8 and E.14.

**Expectations, stated before running.** (1) The simulation will show that at 6 and 10 trials a lower SNR lowers the
measured spread over most of the simulated range, and raises it only at 100 trials, because with few trials each trial
carries a large share of its own template (the development check above). (2) The null check will give a median
$r_\text{matched}$ within ±0.2 of zero in most conditions, because both states are then measured at the same SNR and
trial count. (3) We cannot say in advance whether the matched comparison will be informative: that depends on the SNRs
of the data, which have not been measured; in the development check a 2 ms jitter with 10 trials was seen only above
an SNR of about 6. (4) We do not know which state has the higher SNR in these data; E.9 assumed lower amplitude under
propofol, but no amplitude has been measured. If propofol lowers the SNR, matching adds noise to the awake trials,
which at these trial counts lowers the awake spread, so we expect $r_\text{matched}$ to be at least the $r$ as run
(median 1.28) and, if the comparison is informative, the reading above to find the rise not explained by SNR. If
propofol raises the SNR in most connections, the propofol trials are degraded, which at these trial counts lowers the
propofol spread, and $r_\text{matched}$ will be lower than 1.28; by how much depends on SNRs that have not been
measured, and in that case we make no prediction. (5) The restricted row will keep fewer connections and give a median
close to the as-run median, if $r$ does not depend on the SNR change.

#### E.15.3 R2: monkey-level bootstrap of H2b and H3 (Neurotycho)

**Concern.** The sessions of one monkey are not independent, so tests over sessions (the Wilcoxon test of H2b, the
session bootstrap of H3) may overstate the evidence; the inference should be to monkeys.

**Inference unit.** The monkey. Four monkeys: Chibi and George received every agent; Kin2 and Su received only
ketamine-medetomidine.

**What is computed.** From the per-session result files only, no recording: the confirmatory set
(`results/2026-10-21/confirmatory/`, 20 sessions) and the exploratory set (`results/2026-10-21/exploratory/group_inputs.txt`,
23 sessions), each read exactly as the committed group step reads it (gamma band, sleep sessions left out, H2b
exclusions as recorded). Beside the session-level results, recomputed with the committed group functions (they
reproduce E.14), a two-stage bootstrap with 2,000 resamples and one generator seeded with the committed seed:

- **H2b.** Draw the monkeys with replacement (as many as there are), then, within each drawn monkey, its sessions with
  replacement (as many as it has); recompute the committed effect, the smaller of the two median Kendall $\tau$.
- **H3.** Within each agent, draw with replacement the monkeys that received it, then each drawn monkey's sessions with
  that agent, with replacement; recompute $D = \text{AUC}_\text{lag variability} - \max(\text{AUC}_\text{mean lag}, \text{AUC}_\text{power})$
  with the committed leave-one-agent-out AUC. Resampling within agent keeps every agent in every resample, as the
  committed bootstrap does, so that $D$ stays defined; a monkey that received two agents is drawn separately for each.

For each: the point estimate (identical to E.14), the 95% percentile interval, the share of resamples at or below zero
and the share at or above the SESOI (0.2 in $\tau$, 0.05 in AUC), each as $(1 + k)/(1 + B)$ as in E.7.

**Rule.** Reported without verdict, as a sensitivity analysis of H2b and H3; the verdicts of E.14 stand. With two
monkeys for three of the four agents there are only three distinct monkey draws per agent, and a percentile bootstrap
over $n$ units understates the variance of a mean by a factor $(n - 1)/n$, a half for two monkeys. The monkey-level
interval is therefore a lower bound on the uncertainty at the monkey level: it can show that the session-level
results overstate the evidence, but it cannot show that they understate it.

**Expectations, stated before running.** The point estimates equal E.14 (H2b: 0.06 confirmatory, −0.01 exploratory;
H3: $D$ 0.07 and 0.085). For H2b, the share at or below zero will be near one half, because the smaller median $\tau$
is near zero. For H3, the 95% interval will include zero and be at least as wide as the session-level interval
(−0.23 to 0.20 and −0.21 to 0.23), because the large ketamine AUC rests on two monkeys; H3 stays inconclusive.

#### E.15.4 R3: Michigan reanalysed with one generator per subject (deviation D8)

**Concern.** Under D6 each process seeded its generator once and analysed its subjects in turn, so a subject's random
draws (edge-test surrogates and null realisations) depended on its place in its process, and no subject's result
except sub-02's can be reproduced by analysing that subject alone.

**Deviation D8.** Each subject's generator is seeded with the committed seed plus the number in the subject's name
(sub-02 with 20261023, sub-30 with 20261051), and the seed is written into its result file. Every other step is the
exploratory analysis as run for E.14: the committed code with D1 to D5 (`deviations.py`, unchanged), the same 25
subjects (sub-29 still refused, E.13), the same settings (200 null realisations, 1,000 surrogates). D8 is implemented
in a new module, `reseeded.py`, which replaces only the committed runner's single generator; `deviations.py` and
`exploratory_group.py`, whose hashes are recorded in the earlier results, are not changed. Each subject is now
independent, so the launcher (`launch_reseeded.py`) runs one process per subject, at most ten at a time, longest
expected first, with linear-algebra libraries held to one thread each. It is a dry run unless `--execute` is given,
checks the interpreter, the timing table and every subject's runs by file name before starting, writes one log per
subject and a report with one line per subject and outcome, reports every failure with its subject, command, exit
code and the end of its log, ends with a summary and exits non-zero if any check or subject failed. Re-running it skips every subject whose result exists, so an interrupted run resumes.

**Group step.** Once all 25 files exist, `reseeded.py listing` writes a list of inputs that is the list of E.14
(`exploratory/group_inputs.txt`) with each Michigan file replaced by its reseeded one; it refuses if any is missing,
if any carries a seed other than its D8 seed, or if the folder holds a Michigan file not in the earlier list. The
Neurotycho and PRIOS inputs are the same files as in E.14. The unchanged exploratory group step (D7) then computes the
five primary verdicts with the committed rules and D5.

**Rule.** The D8 verdicts are exploratory and are reported beside those of E.14 (D6). Where they differ, both are
reported and neither replaces the other; the difference measures how much the exploratory results depend on the
random draws. Per subject, the H1 null-A p-value and steepness ratio, the H2a $\tau$ and the H4 $\log H$ are tabulated
beside their D6 values.

**Expectations, stated before running.** The verdicts of E.14 will not change: H1 counts against DPC through the
falsifier (giant component intact through LOR, median 0.95 of its awake size), because the edge threshold is the 99th
percentile of 20 surrogates pooled over every pair of regions and varies little between draws; H2a and H4 stay
inconclusive. Per-subject null-A p-values will move by amounts like sub-05's between its two D6-era analyses (0.025
and 0.065, E.13), and group medians by less.

#### E.15.5 Commands and run times

From the repository root, after the commit. Run times are for the machine that ran E.14 (Apple M2 Pro, one core per
process): R3 from the per-subject times of the D6 run (0.76 to 4.42 h, 55.1 h in all, measured with nine or ten
processes running at once), R1 and R2 from synthetic data of the real size.

```
OUT=analysis/open_data/results/$(date -u +%Y-%m-%d)
PREVIOUS=analysis/open_data/results/2026-10-21/exploratory/group_inputs.txt

# R1. Simulation (about 10 minutes), the seven PRIOS sessions (under a minute each), group step (seconds).
.venv/bin/python -E -s -m analysis.open_data.snr_control simulate --out $OUT/exploratory_snr/snr_simulation.json
for s in data_external/ds004370/sub-*/ses-1; do
  .venv/bin/python -E -s -m analysis.open_data.snr_control prios --session-dir "$s" --out $OUT/exploratory_snr; done
.venv/bin/python -E -s -m analysis.open_data.snr_control group --inputs $OUT/exploratory_snr \
  --simulation $OUT/exploratory_snr/snr_simulation.json --out $OUT/exploratory_snr/snr_group.json

# R2. Monkey-level bootstrap, confirmatory and exploratory inputs (about 10 seconds each).
.venv/bin/python -E -s -m analysis.open_data.monkey_bootstrap --inputs analysis/open_data/results/2026-10-21/confirmatory \
  --out $OUT/exploratory_monkey/monkey_bootstrap_confirmatory.json
.venv/bin/python -E -s -m analysis.open_data.monkey_bootstrap --inputs $PREVIOUS \
  --out $OUT/exploratory_monkey/monkey_bootstrap_exploratory.json

# R3. Michigan with one generator per subject (D8).
# Dry run: plan, checks and expected wall time; starts nothing.
.venv/bin/python -E -s -m analysis.open_data.launch_reseeded --root data_external/ds006623 --previous $PREVIOUS --out $OUT/exploratory_reseeded
# Staged first run on the shortest subject (about 45 minutes), to be checked before the rest.
.venv/bin/python -E -s -m analysis.open_data.launch_reseeded --root data_external/ds006623 --previous $PREVIOUS --out $OUT/exploratory_reseeded --subject sub-26 --execute
# The other 24 subjects (about 5.8 hours on ten processes); sub-26 is skipped because its result exists.
.venv/bin/python -E -s -m analysis.open_data.launch_reseeded --root data_external/ds006623 --previous $PREVIOUS --out $OUT/exploratory_reseeded --execute
# Group step, once all 25 files exist.
.venv/bin/python -E -s -m analysis.open_data.reseeded listing --previous $PREVIOUS --folder $OUT/exploratory_reseeded \
  --out $OUT/exploratory_reseeded/group_inputs.txt
.venv/bin/python -E -s -m analysis.open_data.exploratory_group group --inputs $OUT/exploratory_reseeded/group_inputs.txt \
  --out $OUT/exploratory_reseeded/verdicts_reseeded.json

# Tests of the analysis code (synthetic data only).
.venv/bin/python -I analysis/open_data/run_tests.py
```

R1 and R2 can run while R3 runs, on a core that R3 leaves free (with ten R3 processes on ten cores, wait for R3 or
run R3 on nine).
