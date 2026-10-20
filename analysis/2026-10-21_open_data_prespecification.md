# Pre-specification draft: tests of the predictions on open data

Draft of 21 October 2026, for the authors to review, commit and then paste into the paper as a new appendix (Appendix
E) before any test is run. No test below has been run on real data. Real recordings were only loaded to check their
formats, apart from one dry run on surrogate signals whose output was deleted unread (E.1). The code
(`analysis/open_data/`) was proved on synthetic data only: unit tests whose answers are known and end-to-end runs of
every analysis command on synthetic files laid out exactly like the datasets (the downloader was checked only by
listing files and sizes). The confirmatory runs are to be launched by the lead author only after the code and this
text are committed.

---

## Appendix E. Pre-specified tests of the predictions on open data

### E.1 Purpose and what was seen before the tests were fixed

Every result in Appendices B to D comes from simulation. This appendix fixes, before any analysis, how the predictions
of Section 8 that open data can reach will be tested on recordings made by others, and what result would count
against DPC. The tests, their measures, thresholds and pass rules were written and committed before any of the
datasets was analysed.

Before the tests were fixed we read the datasets' documentation and file layouts, the concentration schedules and
loss and return of responsiveness tables of the Michigan dataset (E.2), the condition markers of one Neurotycho session
and its electrode map, the stimulation and channel tables of one PRIOS patient and the event table of one TMS-EEG
participant, and we loaded the files of one Michigan subject (sub-02) and of 16 channels of one Neurotycho session to
check that they parse, reporting only their sizes, the share of censored volumes and the number of bipolar
derivations. While checking the Neurotycho file format, the first samples and the standard deviation of one raw ECoG
channel were printed. No measure on which a test depends (giant component, coupling, lag, power, latency or any
indicator built from them) was computed on real data and read. Before the authors ruled that no pipeline check may
use real recordings, one dry run of the fMRI pipeline was completed on sub-02's files with the BOLD replaced by
phase-randomised surrogates, which destroy all coupling; its output also held the concentrations at sub-02's real loss
and return of responsiveness, and it was deleted without being opened. Two later dry runs, with placeholder event
times, were stopped before finishing, and their outputs were deleted without being opened. The dry-run option was
then removed from the code, which is proved on synthetic data only (E.11).

Three published results on the same data were known to us when the tests were fixed, and each is a prior against
which a result must be read. On the Michigan dataset, functional connectivity fell gradually during induction while
recovery was abrupt (Huang et al., 2021). On the Neurotycho recordings, cortical dynamics became more stable, not less,
as consciousness was lost under every agent (Solovey et al., 2015), which argues against the critical slowing down of
prediction 2. On the PRIOS recordings, the median latency of the earliest response component lengthened from 22.0 ms
awake to 26.4 ms under propofol (van Blooijs et al., 2024), so a change in mean latency is already known.

### E.2 Datasets checked

Each dataset was opened on 20 October 2026: its licence was read where it is published, its files listed and, where
noted, one sample downloaded and read. Sizes are those reported by the archive.

| Dataset | Licence and access | Size | What it contains | Use here |
|---|---|---|---|---|
| Michigan Human Anesthesia fMRI Dataset-1, OpenNeuro ds006623 v1.0.0 (Huang et al., 2021) | CC0, open | 34.1 GB; 0.54 GB used | 26 volunteers, 4 imagery runs and 2 rest runs (TR 0.8 s), XCP-D parcellated series; effect-site and plasma propofol concentration at every volume; loss of responsiveness (LOR) volume for 26, return (ROR) volume for 20 (6 marked N/A); two stepped protocols, 0.4 to 2.4 µg/ml (14 subjects) and 1.0 to 3.0 µg/ml (12), in steps of 0.4 µg/ml; LOR at 0.8 to 3.0 µg/ml | H1, H2a, H4 |
| Neurotycho "Anesthesia and Sleep" task 78 (Yanagawa et al., 2013) | Copyright waived on neurotycho.org (CC0 wording), open | 32.6 GB used (23 anaesthesia sessions, 5 electrode maps) | 4 macaques, 128-channel subdural ECoG at 1 kHz; ketamine-medetomidine (11 sessions), propofol, ketamine, medetomidine (4 each), sleep (7, not used); markers for awake eyes open and closed, injection, start and end of the anaesthetised condition, recovery; one injection per session, no concentrations, no stimuli | H2b, H3 |
| PRIOS, OpenNeuro ds004370 v1.0.2 (van Blooijs et al., 2024) | CC0, open | 29.6 GB | 7 patients in `participants.tsv` (the README says 6); ECoG at 2048 Hz; single-pulse stimulation awake (clinical session) and under propofol (operating room, on a later day); stimulated pair, current and notes per pulse; no concentrations; co-medication in the operating room not documented in the files checked | H5a (secondary) |
| Allen Institute cortical stimulation, DANDI 000458 (Claar et al., 2023) | CC BY 4.0, open | 361.5 GB, 24 sessions | Mice; 30-channel EEG; Neuropixels LFP and sorted units where probes were used (the 18 larger sessions, by file size); single biphasic pulses to secondary motor cortex at 20, 50 and 100 µA, awake and under isoflurane (1 to 1.5% maintenance), induction epoch marked | Not pre-specified (E.9) |
| TMS-EEG under propofol sedation, OpenNeuro ds005620 v1.0.0 (Bajwa et al.) | CC0 in `dataset_description.json`, CC BY 4.0 in the README; treated as CC BY 4.0 | 83.0 GB | 21 participants (1 excluded by the authors); 64-channel EEG at 5 kHz; TMS awake and in up to three sedated runs; about 185 pulses per run in the participant checked; no concentrations in the files checked | Not pre-specified (E.9) |
| MGH propofol EEG, DANDI 001285 | CC BY 4.0, open | 1.19 GB | One NWB file holding one 64 × 2,316,950 array at 250 Hz (2.6 h) and nothing else: no channel names, no stimulus or response events, no concentrations, no LOR or ROR times | Unusable |
| VitalDB (Lee et al., 2022) | CC BY-NC-SA 4.0 and a data use agreement (no disclosure to others, report misuse within 24 hours, no re-identification) | 6,388 cases | 3,344 cases with raw two-channel frontal EEG and propofol effect-site concentration, of which 3,342 also received remifentanil; no LOR markers | Not used |
| Cambridge propofol EEG (Chennu et al., 2016) | CC BY 2.0 UK as stated on the repository page | 3.44 GB | 20 volunteers; 91-channel resting EEG, preprocessed into 10 s epochs, at baseline, mild and moderate sedation and recovery, with plasma concentration and a two-choice task | Not used |
| Propofol fMRI with a story, OpenNeuro ds003171 v2.0.1 (Kandeepan et al., 2020) | CC0, open | 4.8 GB | 17 volunteers; auditory and rest runs awake, light, deep and recovery; no concentrations in the files checked | Not used |

DANDI 001285 lacks everything a test needs. VitalDB records two frontal channels, which cannot form a network, nearly
every case also received an opioid, there is no LOR marker, and its agreement binds each user, so the authors would
have to accept it themselves. The Cambridge and Kandeepan datasets have four levels without a marked LOR; four points
cannot separate a threshold from a smooth decline.

### E.3 Which predictions open data can test

| Prediction | Testable now? | Dataset and test | What limits it |
|---|---|---|---|
| 1. Giant component collapses at LOR, sharper than local power | Partly | Michigan fMRI, H1 | BOLD at 0.8 s resolves no millisecond timing and no stimulus-locked phase locking; it tests the shape of the collapse of an ongoing coupling network against concentration, not the network of content timing that prediction 1 names |
| 2. Critical slowing down before LOR | Partly | Michigan fMRI, H2a (slow stepped induction); Neurotycho ECoG, H2b (single injection) | fMRI order parameter from co-fluctuations; Neurotycho inductions are fast, not the slow induction the prediction requires, and the anaesthetised marker follows LOR |
| 3. Lag variability, not mean lag, predicts LOR across agents | Partly | Neurotycho ECoG, H3 | Ongoing activity, not responses across trials; awake and anaesthetised states, not the moment of LOR; propofol, ketamine, medetomidine and their combination, no sevoflurane; 4 monkeys |
| 4. Induction excitation scales with sensory load | No | None | No open dataset varies sensory load at induction |
| 5. Inertia tracks thalamocortical coupling | No | None | Needs manipulation of thalamic drive in animals |
| 6. Hub disruption lowers the LOR concentration more | No | None | Needs focal inactivation |
| 7. Ketamine spares internal more than stimulus coherence | No | None | No open recording delivers stimuli under ketamine; Neurotycho's ketamine sessions have none |
| 8. Inter-areal latency variability rises before mean latency | Partly | PRIOS, H5a (secondary) | One deep propofol state against wakefulness, on different days; "just below loss of responsiveness" cannot be reached; mean latency is already known to change |
| 9. Alpha-band phase locking preserved at alpha onset | Possible, not pre-specified | Neurotycho propofol inductions | Four sessions in two monkeys; left exploratory |
| 10. Arousal threshold follows down-states | No | None | No open sleep recording with graded arousing stimuli was found |
| 11 to 13. Myelin, microglia, astrocytes | No | None | Need animal manipulations |
| 14. Sleep against anaesthesia at matched depth | No | None | Neurotycho has sleep and anaesthesia in the same monkeys but no graded arousal and no concentrations |

Prediction 1 in the form stated, a stimulus-locked network during a slow ramp with documented LOR, and predictions 4
to 7 and 10 to 14 cannot be tested with any open dataset we found. The 2013 propofol EEG study with stimuli every 4 s
(Purdon et al., 2013) would serve prediction 1, but its public deposit (DANDI 001285) contains none of the events.

### E.4 Rules common to every test

- **Family and correction.** The primary tests are H1, H2a, H2b, H3 and H4. Their one-sided p-values are corrected
  together with Holm's method at a family-wise α of 0.05. Secondary analyses (E.9) are reported without a verdict.
- **Three outcomes.** A test *supports DPC* if its corrected p-value is below 0.05 and its effect estimate is at least
  the smallest effect size of interest (SESOI) stated with it. It *counts against DPC* if two one-sided tests (Lakens
  et al., 2018) show the effect to lie within ± SESOI, or if the estimate is at or beyond −SESOI. Otherwise it is
  *inconclusive*. Absence of an effect is therefore claimed only through equivalence, as Section 8 requires.
- **Seed and resampling.** Every random step uses seed 20261021 (`analysis/open_data/settings.py`).
- **Exclusions.** A subject or session is excluded from a test only by a rule stated below; the exclusion and its
  reason are written into the result file and listed in the group report.
- **Provenance.** Every result file records the commit, the SHA-256 of every analysis module, every setting and the
  software versions. Any change to the code or settings after the commit of this appendix makes the affected test
  exploratory, and it will be reported as such alongside the result of the committed version.
- **No peeking.** Group verdicts are computed once, by `run.py group`, after every per-subject file exists.

### E.5 H1: is the collapse of the giant component a threshold? (prediction 1, Michigan fMRI)

**Data.** Imagery runs 1 to 4 of every subject in the XCP-D output without global signal regression, band-pass
filtered, in the 156-region parcellation (`4S156Parcels`). Run 1 precedes the infusion (concentration zero
throughout) and is the awake reference; run 2 is the stepped induction. Run 2 has under a minute at zero
concentration (28 volumes in sub-02), too little for one window.

**Preprocessing.** Task-evoked activity is regressed out with the dataset's four instruction regressors
(`Ideal_task{run}_{action,navi,squeeze,tennis}.xmat.1D`). Volumes with framewise displacement above 0.5 mm are
censored; a window with more than 20% censored volumes is dropped.

**Network and order parameter.** Windows of 75 volumes (60 s), stepped by 25 volumes. In each window the Pearson
correlation of every pair of regions is an edge if it exceeds the 99th percentile of correlations between
independently phase-randomised copies of the same window (20 surrogates, pooled over pairs). $S$ is the share of
regions in the largest connected component. Each window is assigned its mean effect-site concentration. The mean
correlation and the mean standard deviation of the regional signals (local amplitude) are kept for each window.

**Shape.** A decreasing four-parameter logistic and a straight line are fitted to $S$ against concentration; the
steepness $k$ of the logistic (its 10 to 90% width is $2\ln 9/k$) is bounded to widths between 0.05 and 20 µg/ml.

**Thresholding control.** Thresholding a network whose coupling declines smoothly already yields a sigmoid giant
component, so the observed steepness is compared with the steepness the same pipeline produces from surrogate data
whose coupling declines smoothly. Each surrogate window mixes a common-phase surrogate of a randomly chosen awake
window (which keeps its correlations) with an independent surrogate (which removes them) in proportions that scale
every correlation by a factor $f$. In null A, $f$ makes mean coupling fall on a straight line in concentration from its
awake level to its level in the top 20% of concentrations. Each null is realised 200 times and fitted like the data.
In null B (secondary), $f$ follows the observed mean coupling of each window exactly, which asks whether the network
falls more abruptly than its mean coupling.

**Statistic.** For each subject, $x = \log(k_{\text{observed}} / \text{median } k_{\text{null A}})$. Group test: one-sided
Wilcoxon signed-rank test of $x > 0$. Effect: the median of $x$. SESOI: $\log 1.5$ (a collapse at least 1.5 times as
steep as the smooth-decline null).

**Pass rule.** Supports DPC as in E.4, and only if the median of $x$ is also positive with the edge test at α of 0.001
and of 0.05 (null A recomputed at each). Counts against DPC as in E.4, or if the giant component stays intact through
LOR: the median over subjects of mean $S$ after LOR divided by mean awake $S$ is at least 0.9 (the falsifier stated
in Section 8). **Measurement gate:** if BOLD coupling does not fall with concentration (median over subjects of deep
over awake mean coupling at least 0.9), the fMRI network does not register the drug and H1 is reported as not
evaluable rather than as evidence either way.

**Secondary, reported without verdict.** The sigmoid against line comparison (number of subjects with a Bayesian
information criterion lower by at least 10 for the sigmoid); steepness relative to null B; the ratio of the steepness
of $S$ to that of local amplitude (prediction 1's "sharper than local power"; SESOI 1.5); and the distance between the
sigmoid midpoint and the concentration at LOR, tested for equivalence within ±0.4 µg/ml (one concentration step).

### E.6 H2a and H2b: critical slowing down before LOR (prediction 2)

**H2a, Michigan fMRI.** The order parameter is computed at every volume from edge co-fluctuations (Zamani Esfahlani
et al., 2020): each region's residual signal is standardised on the awake run, the product $z_i z_j$ of every pair is
an edge if it exceeds the 99th percentile of the same products between independent surrogates of the awake run, and
$S(t)$ is the giant component. The segment runs from the first volume with non-zero concentration in run 2 to the LOR
volume. Censored volumes are interpolated; a subject with more than 20% of that segment censored is excluded.

**H2b, Neurotycho ECoG.** For each anaesthesia session, from the injection marker to the start of the anaesthetised
condition. Bipolar derivations, filtering and the long-range pairs are as in E.7; in consecutive 2 s windows the
gamma-band (30 to 45 Hz) phase-locking value of every long-range pair is an edge if it exceeds the 99th percentile of
the same pairs with one member circularly shifted by at least 0.5 s (20 shifts), and $S(t)$ is the giant component
over all derivations. The start of the anaesthetised condition was marked after LOC was established, so the segment
can include a few minutes after LOC; this biases against finding a rise before LOC only if the rise is confined to
the last minutes.

**Indicators (both).** Following Dakos et al. (2012): Gaussian detrending with a bandwidth of 10% of the segment,
variance and lag-1 autocorrelation in a rolling window of half the segment, and Kendall's $\tau$ of each against time.
Per subject or session, a one-sided p-value against 1,000 phase-randomised surrogates of the same segment is reported.

**Statistic and pass rule.** For each indicator, a one-sided Wilcoxon signed-rank test of $\tau > 0$ across subjects
(H2a) or sessions (H2b). Both indicators must rise: the test's p-value is the larger of the two, and its effect is the
smaller of the two median $\tau$. SESOI: $\tau = 0.2$. Counts against DPC if both indicators are shown to lie within
±0.2, or if either median is at or below −0.2. A failure of H2b is weaker evidence than a failure of H2a, because the
Neurotycho inductions are not slow; Section 8 states the falsifier for "carefully controlled slow induction".

### E.7 H3: does lag variability, rather than mean lag or power, track loss of responsiveness across agents? (prediction 3, Neurotycho ECoG)

**Sessions.** The 23 anaesthesia sessions of task 78. Task 75 holds three recordings from two of the same days and monkeys and is not used. All channels
present in every recording of the session are used. A session lacking the awake eyes-closed or anaesthetised markers
is excluded.

**Epochs.** Awake blocks come from the awake eyes-closed condition and anaesthetised blocks from the anaesthetised
condition. The monkeys wore an eye mask from the eyes-closed condition until recovery, so eye closure is matched.

**Preprocessing.** Notch filters at 50, 100 and 150 Hz (quality 30). Bipolar derivations between each electrode and
its nearest neighbour on the session's electrode map (the map of the same monkey by the same experimenter). Pairs of
derivations that share no electrode and are further apart than the median distance between derivations are
long-range pairs; only these enter the coupling measures, which limits volume conduction without discarding coupling
near zero lag. Fourth-order Butterworth band-pass filtering, applied forwards and backwards, with 2 s margins, and the
analytic signal.

**Measures.** In 30 s blocks, divided into 1 s windows, for every long-range pair: the circular mean phase difference in
each window; across the 30 windows, the *lag variability* (circular standard deviation, in ms at the band's centre
frequency) and the absolute *mean lag* (ms). Per block, these are averaged over pairs; *local power* is the mean log
power of the derivations. The phase-locking value (lag-sensitive, includes zero lag) and the weighted phase lag index
(Vinck et al., 2011; blind to zero lag) are computed alongside. Each measure is standardised against the session's
awake blocks.

**Muscle.** A block is dropped if its 70 to 150 Hz power exceeds the median of blocks in the same state by more than
five median absolute deviations (minimum deviation 0.05 in log power). The reference is the same state because
ketamine raises high-frequency power across the cortex. The rule removes bursts, not tonic muscle activity; the beta
band (13 to 30 Hz), which muscle contaminates less, is analysed as a secondary band for that reason.

**Contrast.** For each measure, the direction of its change from awake to anaesthetised is learned on the other agents
and applied to the held-out agent, and the area under the ROC curve (AUC) separating that agent's awake from
anaesthetised blocks is computed; the four agent AUCs are averaged. A measure that changes in opposite directions
under different agents, as power does between propofol and ketamine, cannot predict LOR across agents. The
statistic is $D = \text{AUC}_{\text{lag variability}} - \max(\text{AUC}_{\text{mean lag}}, \text{AUC}_{\text{power}})$.

**Test and pass rule.** Primary band gamma (30 to 45 Hz), the band of the model's 40 Hz reference. A bootstrap over
sessions, resampled within agent (2,000 resamples), gives a one-sided p-value (share of resamples with $D \le 0$) and a
95% interval. SESOI: 0.05 in AUC. Supports DPC as in E.4. Counts against DPC if mean lag or power predicts as well as
or better than lag variability, that is if the share of resamples with $D \ge 0.05$ is below 0.05 (the falsifier stated
in Section 8). Theta, alpha and beta bands, and the phase-locking value and weighted phase lag index, are reported
without verdict. Monkey and agent are partly confounded (two monkeys received only the combination), which the
report states.

**Signal-to-noise.** Lower power makes phase estimates noisier, which by itself raises lag variability. The gamma
power falls under propofol and rises under ketamine, so a rise in lag variability under both agents is not explained
by signal-to-noise alone; under propofol alone it could be, and the per-agent AUCs are reported so that this can be
seen.

### E.8 H4: hysteresis between induction and emergence (Michigan fMRI)

**Data.** As H1; the induction curve uses runs 1 and 2, the emergence curve runs 3 and 4 (run 3 alone for sub-29,
which lacks run 4).

**Measure.** The sigmoid midpoint of $S$ against concentration on induction ($c_{50,\text{ind}}$) and on emergence
($c_{50,\text{em}}$); network hysteresis $H = c_{50,\text{ind}} / c_{50,\text{em}}$. Behavioural hysteresis is the
concentration at LOR divided by that at ROR, for the 20 subjects with an ROR volume.

**Pharmacokinetic sensitivity.** A wrong effect-site model creates hysteresis by itself. The effect-site series is
therefore also recomputed from the dataset's plasma series with a first-order effect compartment at five equilibration
rate constants, 0.2, 0.26, 0.456, 0.8 and 1.21 per minute, starting each run from the dataset's effect-site value.
0.2 and 1.21 per minute correspond to the equilibration half-lives of 3.5 min and 34 s compared by Struys et al.
(2000), 0.456 per minute is the value of Schnider et al. (1999), and 0.26 and 0.8 fill the range between them.
The pharmacokinetic model behind the dataset's own series is not stated in the files checked.

**Statistic and pass rule.** One-sided Wilcoxon signed-rank test of $\log H > 0$; SESOI $\log 1.05$. Supports DPC only
if the largest p-value over the six effect-site series, after Holm correction, is below 0.05 and the smallest median
$\log H$ is at least $\log 1.05$. Counts against DPC if, with the dataset's own effect-site series, $\log H$ is shown to
lie within $\pm\log 1.05$ or its median is at or below $-\log 1.05$. Secondary: the Spearman correlation between network
and behavioural hysteresis across subjects. The paper's own models disagree on hysteresis (Section 10, limitation 9),
so a failure here bears on P5's percolation form, not on P1 to P3.

Emergence follows the end of the infusion, so its concentration falls continuously while induction rose in held
steps; time at each concentration differs between the two curves, which the effect-site sensitivity analysis only
partly addresses.

### E.9 Secondary and deferred analyses

**H5a, PRIOS (prediction 8, partial).** For each patient, the awake and propofol recordings; both polarities of a
stimulated pair pooled; pulses whose notes report a deviation from the requested current excluded; response
electrodes at least 20 mm (in the dataset's MNI coordinates) from both stimulated electrodes and marked good. Trials
from -500 to 120 ms around the pulse, baseline subtracted (median from -500 to -10 ms); a connection responds if the
mean response from 9 to 100 ms exceeds 3.4 baseline standard deviations in both states. Trial counts are equalised
by random subsampling (at least 6). Mean latency is that of the largest negative deflection of the mean response;
single-trial latency is the shift, within ±20 ms and refined by parabolic interpolation, that best aligns each trial
with the mean response, and its spread is the scaled median absolute deviation. Per connection,
$r = \log(\text{SD}_{\text{prop}}/\text{SD}_{\text{awake}}) - \log(\text{latency}_{\text{prop}}/\text{latency}_{\text{awake}})$,
positive when variability rises more than mean latency; per patient, the median $r$. One-sided Wilcoxon test over
patients, SESOI $\log 1.2$, reported without verdict because 7 patients, one deep state and two different days make it
a weak test. Confounds: the propofol recordings were made in the operating room at electrode removal, with unknown
co-medication; lower response amplitude under propofol makes single-trial latencies noisier.

**Not pre-specified.** DANDI 000458 could test the second half of prediction 8, that single-neuron timing stays
precise while timing between areas varies, but its units table has not been inspected, so no analysis of it is fixed
here. The TMS-EEG dataset needs source reconstruction to separate areas. Prediction 9 on the four Neurotycho propofol
inductions is left exploratory. Any of these, if run, will be labelled exploratory unless a separate prespecification
is committed first.

### E.10 Confounds and how they are handled

| Confound | Where | Handling |
|---|---|---|
| Thresholding a smooth decline | H1, H4 | Null A and null B surrogates through the identical pipeline (E.5); three edge thresholds |
| Volume conduction | H2b, H3 | Bipolar derivations; only long-range pairs sharing no electrode; wPLI reported beside the lag-sensitive measures |
| Signal-to-noise | H3 | Cross-agent design (power falls under propofol, rises under ketamine); per-agent AUCs reported |
| Muscle | H3 | Within-state outlier blocks dropped; beta band as secondary |
| Eye closure | H3 | Awake reference is the eyes-closed condition, matched to the eye mask under anaesthesia |
| Head motion | H1, H2a, H4 | Framewise displacement censoring at 0.5 mm; windows over 20% censored dropped |
| Task-evoked co-activation | H1, H2a, H4 | Instruction regressors removed before any coupling |
| Pharmacokinetic lag | H4 | Effect-site recomputed at five equilibration constants |
| Opioids | All | None in the Michigan or Neurotycho protocols as documented; PRIOS co-medication unknown, stated |
| Fast induction | H2b | Stated as weaker than H2a; the prediction's falsifier requires slow induction |
| Prior results on the same data | H1, H2b, H5a | Stated in E.1 |

### E.11 Commands, downloads and run times

From the repository root, with the repository's Python 3.13 environment (NumPy 2.5.4, SciPy 1.18.1; nothing else is
needed). `-I` isolates the interpreter so that no file in the data folders can be imported.

```
# 1. Downloads: each command lists files and sizes and writes nothing; add --execute to download.
.venv/bin/python -I analysis/open_data/download.py michigan      # 434 files, 0.54 GB
.venv/bin/python -I analysis/open_data/download.py neurotycho    # 28 archives, 32.6 GB (about twice that on disk after extraction)
.venv/bin/python -I analysis/open_data/download.py prios         # 114 files, 29.6 GB

# 2. Loader checks: no statistic is computed.
SUBJECTS=$(tail -n +2 data_external/ds006623/derivatives/LOR_ROR_Timing.csv | cut -d, -f1 | sed 's/^/--subject /')
.venv/bin/python -I analysis/open_data/run.py michigan --root data_external/ds006623 $SUBJECTS --out unused --check-only
for e in data_external/neurotycho/*_mat_ECoG128; do .venv/bin/python -I analysis/open_data/run.py neurotycho --experiment "$e" --out unused --check-only; done

# 3. Confirmatory runs.
OUT=analysis/open_data/results/$(date -u +%Y-%m-%d)
.venv/bin/python -I analysis/open_data/run.py michigan --root data_external/ds006623 $SUBJECTS --out $OUT
for e in data_external/neurotycho/*_mat_ECoG128; do .venv/bin/python -I analysis/open_data/run.py neurotycho --experiment "$e" --out $OUT; done
for s in data_external/ds004370/sub-*/ses-1; do .venv/bin/python -I analysis/open_data/run.py prios --session-dir "$s" --out $OUT; done
.venv/bin/python -I analysis/open_data/run.py group --inputs $OUT --out $OUT/verdicts.json

# 4. Secondary bands for H3 (reported without verdict).
for b in theta alpha beta; do for e in data_external/neurotycho/*_mat_ECoG128; do
  .venv/bin/python -I analysis/open_data/run.py neurotycho --experiment "$e" --band $b --out $OUT; done; done

# Tests of the analysis code (synthetic data only).
.venv/bin/python -I analysis/open_data/run_tests.py
```

Run times on the machine that wrote the code (Apple M2 Pro, one core per process), measured on synthetic data of the
real size, never on real recordings: Michigan, 1,123 s (19 minutes) for one subject of 156 regions with runs of
1,145, 2,270, 2,270 and 1,145 volumes at the full settings, measured while other work ran on the machine, so about
8 hours for 26 subjects; Neurotycho, about 3.4 s per 30 s block and 1.1 s per 2 s window of the induction on noise
at full montage size (127 derivations, 3,903 long-range pairs), so about 8 minutes per session and 3 hours for 23;
PRIOS, not measured. Downloads depend on the connection.

### E.12 What open data cannot test

No open dataset combines repeated stimuli, a slow concentration ramp, documented loss and return of responsiveness
and recordings dense enough for a network of phase locking between areas. Prediction 1 in its stated form, the
stimulus-locked part of predictions 3 and 8, prediction 7 and every prediction that needs an intervention or a graded
arousal stimulus (4, 5, 6, 10 to 14) therefore remain untested by this appendix. A pass of every test above would
show that functional networks of ongoing activity behave as DPC predicts at the resolution of fMRI and ECoG; it would
not show that the timing of content between areas fails as P2 to P4b propose.

### References for this appendix (to be merged into the reference list)

Claar, L. D., Rembado, I., Kuyat, J. R., et al. (2023). Cortico-thalamo-cortical interactions modulate electrically evoked EEG responses in mice. *eLife*, 12, RP84630. https://doi.org/10.7554/eLife.84630

Chennu, S., O'Connor, S., Adapa, R., Menon, D. K., & Bekinschtein, T. A. (2016). Brain connectivity dissociates responsiveness from drug exposure during propofol-induced transitions of consciousness. *PLOS Computational Biology*, 12(1), e1004669. https://doi.org/10.1371/journal.pcbi.1004669

Dakos, V., Carpenter, S. R., Brock, W. A., et al. (2012). Methods for detecting early warnings of critical transitions in time series illustrated using simulated ecological data. *PLoS ONE*, 7(7), e41010. https://doi.org/10.1371/journal.pone.0041010

Kandeepan, S., Rudas, J., Gomez, F., et al. (2020). Modeling an auditory stimulated brain under altered states of consciousness using the generalized Ising model. *NeuroImage*, 223, 117367. https://doi.org/10.1016/j.neuroimage.2020.117367

Lee, H.-C., Park, Y., Yoon, S. B., et al. (2022). VitalDB, a high-fidelity multi-parameter vital signs database in surgical patients. *Scientific Data*, 9, 279. https://doi.org/10.1038/s41597-022-01411-5

Vinck, M., Oostenveld, R., van Wingerden, M., et al. (2011). An improved index of phase-synchronization for electrophysiological data in the presence of volume-conduction, noise and sample-size bias. *NeuroImage*, 55(4), 1548–1565. https://doi.org/10.1016/j.neuroimage.2011.01.055

Yanagawa, T., Chao, Z. C., Hasegawa, N., & Fujii, N. (2013). Large-scale information flow in conscious and unconscious states: an ECoG study in monkeys. *PLoS ONE*, 8(11), e80845. https://doi.org/10.1371/journal.pone.0080845

Zamani Esfahlani, F., Jo, Y., Faskowitz, J., et al. (2020). High-amplitude cofluctuations in cortical activity drive functional connectivity. *Proceedings of the National Academy of Sciences*, 117(45), 28393–28401. https://doi.org/10.1073/pnas.2005531117

Datasets: Huang, Z., et al. (2025). Michigan Human Anesthesia fMRI Dataset-1. OpenNeuro ds006623 v1.0.0, https://doi.org/10.18112/openneuro.ds006623.v1.0.0. van Blooijs, D., Blok, S., Huiskamp, G. J. M., & Leijten, F. S. S. (2023). PRIOS. OpenNeuro ds004370 v1.0.2, https://doi.org/10.18112/openneuro.ds004370.v1.0.2. Neurotycho Anesthesia and Sleep task, RIKEN Brain Science Institute, https://neurotycho.org/anesthesia-and-sleep-task. Already in the reference list: Huang et al. (2021), Lakens et al. (2018), Purdon et al. (2013), Solovey et al. (2015), van Blooijs et al. (2024).

---

## Notes for the authors (not for the appendix)

- The equilibration constants of E.8 need a citation per value before publication; 0.456 per minute is commonly given
  for the Schnider model, but the source was not read here, and the other values were chosen to bracket it.
- Section 9.2 asks for the model of Section 4 to be fitted to $S$ to estimate $\pi_c$, $q^*$ and $\lambda$. That fit is
  not pre-specified here, because the fMRI $S$ is not the timing-coherent giant component of the model; reporting the
  sigmoid midpoint and width is what the data support.
- The README of ds004370 says 6 patients; `participants.tsv` lists 7. The analysis uses every session folder present.
- The two Su electrode maps differ (2011 and 2013); the code uses the map by the recording's experimenter.
- VitalDB, if wanted later, needs each author to accept its data use agreement; derived data could not be released
  under the repository's CC BY licence because of its NonCommercial-ShareAlike terms.
