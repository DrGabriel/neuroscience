# Data assessment, 20 October 2026

An assessment of every current report and diagnostic, and a check of the paper against them. Five reviewers worked
on a copy of the English paper in which 10 numbers had been changed on purpose; all 10 were found (several by more
than one reviewer). Every finding below was then re-computed from the report JSON before being listed here; reviewer findings not re-computed are left out. Post hoc
readings are labelled; none changes a verdict fixed before its run.

## 1. Errors in the paper (to correct)

| # | Where | Paper says | Data | Source |
|---|---|---|---|---|
| E1 | Section 5.4 | largest ratio "2.05 at level 0" | 2.0449, so 2.04 | calibration_feedback, model_ratio |
| E2 | Section 4.5 | the only one-step hysteresis was in one *Drosophila* seed | also two human reference runs (seed 20261018, with and without stimulus), gone with twice the time, and one human seed (20261021) that gained one step with twice the time; none exceeds one step | convergence, hysteresis_width |
| E3 | Section 3.3, Section 6, Appendix D | with learning, quorum lost "below 0.13 times the EC50 with every agent" | true without conduction delays; with delays the mean loss is 0.735 (0.15 to 1.00), and learning raised awake coherence from 0.409 to 0.624 in 20 of 20 seeds | learned_timing |
| E4 | Limitation 31 | the floor "also falls as coherence falls"; the worm's remaining broadcast is "no greater" than the phantom | under K1 the phantom floor does not fall with dose; with the 4x window the applied stimulus exceeds the phantom at the deepest dose in 15 of 20 worm seeds, though by less than half of the awake excess | phantom_stimulus |
| E5 | Section 6, C4 row | "Held from 1,000 nodes up" | 19/20 at 302 nodes: by the paper's own rule (every seed at every size) C4 did not hold | validation |
| E6 | Limitation 29 | C5 "9 of 20 seeds at 10,000 nodes" with lambda calibrated to 1.11 | correct, but from an archived report (validation_full_20261018T123515Z, before the code corrections); the text should name it | archive |
| E7 | Limitation 30 | hub activity "1 to 19%"; regions "cycled at about 10 Hz" | 1 to 19% is the group mean at the highest concentration only; the 10 Hz is a linear-stability estimate, not a simulated oscillation | congestion, deafferented_states |
| E8 | Abstract, Sections 6 and 10 (item 26), Conclusion | connectome thresholds "within 2 to 5%"; quorum lost at "85 to 90%" failure | both hold for undirected wiring; on directed wiring quorum needs 1.3 to 3.4 times as many coherent connections and is lost at 61 to 87% failure | percolation |
| E9 | Abstract, Section 6, Conclusion | fluctuations rise at least tenfold before the collapse (T1b), stated generally | holds in most *C. elegans* and human conditions, but 0/20 with measured conduction delays (human), 0/6 in the fly with the NMDA-antagonist-like agent, signed connections or a stimulus, and 3/20 (worm) and 1/6 (fly) without reference feedback | species, re-computed with the study's own function |
| E10 | Section 5.1 | the synchrony surge is presented as narrowed to coupling 1 by the confirmatory run | already specific to coupling 1 in the exploratory run: 29/30 seeds at coupling 1, 18/30 at 0.5, 1/30 at 2 (confirmatory 27/30, 11/30, 7/30) | congestion |

## 2. Design flaw found

**A1 could not have passed.** Global sleep silences half the populations (share 0.5); removing the astrocytic half
leaves 0.25, the state of test O4, which loses quorum in every seed because the sleep threshold is about 0.152. A1
therefore says nothing about astrocytes: P9's astrocytic route is untested, not refuted. The paper counts it among
the failed mechanisms (Abstract, Conclusion).

## 3. Verified results, by postulate (what the data show)

- **P3 quorum.** Thresholds from the degree distribution match measurement within 2 to 5% on undirected wiring;
  within seed spread for *C. elegans* and human, not for the fly (0.0415 against 0.0438 ± 0.0002). Directed wiring
  is much harder to percolate (see E8).
- **P4 two failure routes.** Both abolish quorum in every model and connectome. Close to built in.
- **P4b timing.** Constant offsets are not harmless in the models (S4, D1). Learned arrival times first compensated
  conduction delays (awake coherence 0.409 to 0.624, 20/20) and then dissolved agreement by drift (L1, L3, L4 failed).
- **P5 inertia.** Percolation only, and size-dependent: hysteresis 0.085 at 302 nodes to 0.054 at 1,000,000; the
  ratio drifts from about 1.10 to 1.07 through the calibrated 1.08. Gone after hub lesion at 100,000 and 1,000,000
  nodes. None in the phase model at any setting tried.
- **P6 default dynamics.** Untestable in this Wilson-Cowan model (limitation 30).
- **P7 arousal.** C6 holds in every seed at every size.
- **P8.** F3 failed; B1 and B2 (batching, backoff) are not in the main text; B2 is undefined in most runs because 1 s
  windows cannot resolve slower gaps.
- **P9.** Consistency checks only; A1 uninformative (Section 2).
- **Ketamine (K1).** As specified, held in about half the seeds. Post hoc, on *C. elegans*: with the phantom floor
  subtracted, K1 holds in 16/20 seeds; with the 4x window, in 20/20 by both the corrected and the original criterion.
  On the human connectome the stimulus barely spreads even awake, so K1 cannot be read there.

## 4. Unexploited data (post hoc, verified)

1. **Islands of coherence appear without the shared reference.** Local coherence outlasts global in 18/20 *C. elegans*,
   5/6 *Drosophila* and 18/20 human runs without reference feedback (GABAergic-like agent), and in none of the same
   runs with it; with a sensory stimulus, islands also formed with the reference (10/20 *C. elegans*, 6/6 *Drosophila*). This bears on the ketamine and dreaming account.
2. **Reference feedback delays loss in the phase model** (loss 0.99 to 1.39 worm, 1.00 to 1.40 fly, 1.09 to 1.57 human
   without and with feedback) and widens the transition, the opposite of the percolation model, where it sharpens it.
3. **Constant delays cost coherence even awake:** with measured conduction delays awake coherence on the human connectome
   is 0.409, against 0.965 without.
4. **Stronger Wilson-Cowan coupling leaves hubs less active after collapse** (group means at the highest concentration:
   14 to 19% of awake at coupling 0.5, 5 to 6% at 1, about 1% at 2), and the synchrony surge is a coupling-1 effect.

## 5. Robust and fragile

- Robust: two failure routes; quorum threshold on undirected wiring; T1b in most conditions; C6; the worm K1
  disconnection once the floor is removed.
- Fragile: inertia (size, lesions, model); C5 outside reference parameters (sensitivity);
  every broadcast-based verdict (floor); T1b with delays or signed connections.

## 6. Corrections applied (20 October 2026)

E1 to E10 were corrected in both papers, with the matching Appendix D rows regenerated. Decided with the authors:
A1 is reported as uninformative, so P9's astrocytic route is untested and the count of failed mechanisms is seven; K1
is stated everywhere as failed as specified, with the post hoc floor-corrected reading (16 of 20 *C. elegans* seeds)
named as such; the islands finding is one post hoc sentence in Section 6. The explainer was brought into line in its
four languages (threshold wording, K1, predictions 7 and 13).

## 7. K1c, the pre-specified test of the post hoc ketamine reading (20 October 2026)

Fixed in Appendix C.11 and committed before the run (commit at 16:35:00 UTC, run from 16:35:16 to 17:09:58 UTC, clean
tree). On *C. elegans* K1c passed in 20 of 20 seeds: quorum held at 94% of its awake value or more, and the broadcast
above the phantom floor fell to a median of 13% of its awake value (at most 31%). On the human connectome only 2 of 20
seeds had an awake broadcast at least twice the floor, so the test was not evaluable, as stated before the run.
Recomputed independently from the run data. The report's design record lists the study-wide 838 measurement steps; the
runs used 3,351 (condition names, window of eight cycles, run times 3.3 to 3.4 times those of K1); the code now records
the window used. Consequence for the paper: the sensory-pathway account of ketamine is shown on one connectome and is no
longer counted among the failed mechanisms (six, not seven); ketamine's preserved complexity and dreams stay open.
