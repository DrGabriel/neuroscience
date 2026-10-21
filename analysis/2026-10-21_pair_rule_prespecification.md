# Pre-specification draft: when a connection between two populations counts

Draft of 21 October 2026, for the authors to review, commit and then paste into Appendix C (as C.13) before the full
study is run. Nothing below has been run in full. The code was checked with unit tests and with one smoke run
(`--smoke`: *C. elegans* only, one seed, two concentrations, the shortest integration). The full study is to be
launched by the lead author only after the code and this text are committed. The reference list needs one new entry,
given at the end.

---

### C.13 Pre-specified test of the pair rule: one timing draw per anatomical connection

The tests below, their conditions, seeds and pass rule were written into this paper and committed before the study
that evaluates them was run (`simulator/dpc_pair_rule_study.py`, with `simulator/connection_pairs.py` and
`simulator/dpc_readout.py`). Before that, the code was checked with unit tests and with one smoke run (*C. elegans*
only, one seed, two concentrations, the shortest integration). Its outcomes were computed and read while the code was
checked; with one seed and two concentrations they are not part of the results and did not inform the expectations
below.

**Why this study.** The DPC readout of Appendix C.12 treats every directed arc of a connectome as a separate
connection with its own timing draw, and links two populations in the undirected giant component if either arc
between them is on time. DPC never defined when a connection between two populations counts, so this was a modelling
choice, and it is not neutral across the three connectomes. The human connectome comes from diffusion MRI, which
records no direction, so each of its 17,865 fibres is stored as two arcs, and in C.12 every fibre had two independent
chances to be on time in each cycle. On the other two connectomes the arcs carry measured direction, and most pairs of
populations are linked one way only:

| Connectome | Populations | Arcs | Anatomical connections | Linked both ways | Chances per connection in C.12 |
|---|---|---|---|---|---|
| *C. elegans* | 300 | 5,764 | 3,465 | 1,579 (46%) | 1.66 |
| *Drosophila* | 138,639 | 2,700,513 | 2,511,789 | 188,724 (7.5%) | 1.08 |
| Human | 998 | 35,730 | 17,865 | 17,865 (100%) | 2.00 |

An anatomical connection is an unordered pair of populations linked by at least one arc. In *C. elegans*, 720 of the
5,764 arcs repeat a direction already present between the same two neurons (a chemical synapse and a gap junction in
the same direction), so some pairs had three chances in C.12.

T2b-D, the test that timing variability alone abolishes DPC quorum, failed on the human connectome in C.12 (0 of 20
seeds) while it passed on *C. elegans* (20 of 20) and *Drosophila* (6 of 6). After that result had been seen, a post
hoc diagnostic (`simulator/pair_rule_diagnostic.py`, seed 7, 20 draws) asked whether the failure could come from the
counting alone. It runs no oscillators: every arc is on time independently with the static probability of C.12's
baseline at three times the EC50 of the NMDA-antagonist-like agent, $(1 - p)\,\mathrm{erf}(W/(2\sqrt{2}\sigma_{\text{eff}}))$
with $\sigma_{\text{eff}}$ = 39.6 ms, which is 0.024, and the giant component is read under each rule below:

| Connectome | One draw per connection | Both directions | Either direction (C.12) |
|---|---|---|---|
| *C. elegans* | 0.05 | 0.02 | 0.17 |
| *Drosophila* | 0.30 | 0.28 | 0.32 |
| Human | 0.10 | 0.00 | 0.66 |

On the human connectome the share of populations in the giant component is 0.66 when every fibre has two chances
and 0.10 when it has one, well below $q^*$ = 0.5; on the other two it stays below $q^*$ under every rule. The
diagnostic was first run, with a different draw sequence, as a one-off command whose figures (0.64 and 0.09) were
those seen when the rule was chosen; the script reproduces it. It is static: it leaves out the oscillator dynamics,
which in C.12 did not reliably bring the timing loss forward (T0b-D failed on all three connectomes), so it estimates the
counting effect, not the phase model's loss. If each arc is on time with probability $p$ and the two arcs of a fibre
are independent, a fibre counts with probability $1 - (1 - p)^2$ rather than $p$; when few connections are on time this
almost doubles the share of counting fibres, which in the dense human wiring (a mean of 35.8 connections per
population) is enough to keep a giant component. The human failure of T2b-D may therefore come from how the readout
counts a diffusion-MRI fibre rather than from the network.

**What this study is, and what it is not.** The authors chose the primary rule below after the diagnostic had been
seen. This is a pre-specified test on fresh seeds informed by a post hoc finding, and it is weaker evidence than a
blind test: the expected result on the human connectome is largely a prediction from the diagnostic, so a pass would
confirm that diagnosis on new realisations, not support P4(b) independently. The verdicts of Appendix C.12 stand as
reported. In particular, T2b-D fails on the human connectome under the readout that was fixed before C.12 ran, and
that verdict is reported beside this one, not replaced by it.

**Why neither "every fibre two-way" nor "every fibre one-way" can be assumed.** In macaque cortex, where
interareal connections were measured with tract tracing rather than inferred from diffusion, 66% of the possible
connections between the areas studied exist, and unidirectional connections are unexpectedly common (Markov et al.,
2014). Diffusion MRI cannot tell which human fibres carry axons in one direction or both. A rule that gives every
human fibre two independent chances assumes that every fibre is two independent connections; a rule that reads only
the arcs of one direction assumes that none is. The primary rule counts what the data record, one fibre as one
connection, and the two bounds below bracket the possibilities that the data cannot separate.

#### The pair rules

The dynamics are unchanged, and so is every reading of C.12: the readout only adds three readings of the same
counting connections. A unit test checks that every earlier reading of a sweep is identical, to the last bit, to that
of the code that produced C.12 (commit `adc63f6`), and another that the either-direction rule reproduces C.12's
giant-component reading exactly at every concentration. A connection's arcs are timed exactly as in C.12: an arc
$j \to i$ is on time in a cycle when it transmits and $|\delta_{ji}| \le W/2$, with $\delta_{ji}$ its timing error
relative to the shared rhythm.

- *One timing draw per anatomical connection (primary).* Each anatomical connection is read on one canonical arc: the
  first arc, in the connectome's order, from the lower-indexed to the higher-indexed population when such an arc
  exists, otherwise the first arc the other way. The connection counts in a cycle when that arc transmits and is on
  time, so each connection has one failure draw and one timing draw, as in the percolation model and in the threshold
  theory of Appendix B.5. The choice of canonical arc is fixed by the wiring, not by which arc happens to be on time.
- *Both directions on time (lower bound).* A connection with arcs both ways counts only when it is on time both ways;
  one with arcs one way only counts when that arc is on time. Each direction is read on its first arc, so a repeated
  arc in one direction gives no extra chance.
- *Either direction on time (upper bound).* A connection counts when any of its arcs transmits and is on time: the
  rule C.12 used.

In every cycle the connections counting under the both-directions rule are among those counting under the primary
rule, which are among those counting under the either-direction rule, so the giant component can only be smaller
under the stricter rules (checked by a unit test). Quorum, the quorum at a concentration and the loss concentration
are defined as in C.12, with the counting connections of the rule in force taken as undirected links. The share of
counting connections under a rule is the share of the anatomical connections that count.

#### Conditions, seeds and pass rule

Conditions: the GABAergic-like and the NMDA-antagonist-like agent with the global reference, on *C. elegans*,
*Drosophila* and the human connectome, every other parameter at its reference value (Appendix C.1), with C.12's
integration (838 measurement steps of 0.05, one cycle sampled per jitter correlation time, 42 cycles per
concentration) and concentration grid (0 to 3 times the EC50 in steps of 0.05, 0.1 for *Drosophila*). No rewired, wired
or weaker-coupling condition is run.

Seeds: from the base seed plus 6000 (seeds 20,267,017 onwards), 20 for *C. elegans*, 6 for *Drosophila* and 20 for the
human connectome. Earlier studies used offsets 0 to 19, 1000, 2000, 3000 and 4000, and C.12 used 5000, 5500 and 5600,
so no seed of this study has been run before.

Pass rule: C.12's. A test passes for an organism when the lower bound of the Wilson 95% interval for the share of
seeds in which it holds lies above one half (15 of 20 and 6 of 6 seeds pass; 14 of 20 and 5 of 6 do not). A seed in
which quorum under the primary rule does not hold even at zero concentration counts as failing T2a-1 and T2b-1. There
are three tests per connectome, and no correction for multiple comparisons is made.

#### Tests

- T2a-1: the GABAergic-like agent abolishes DPC quorum under the primary rule within the concentration range (a loss
  concentration under the primary rule exists).
- T2b-1: the NMDA-antagonist-like agent abolishes DPC quorum under the primary rule within the concentration range.
- SP1-1 (paired by seed, per connectome): at their losses under the primary rule, the two agents leave more similar
  shares of counting anatomical connections than effective couplings $K_{\text{eff}}$, compared as absolute log
  ratios, as in SP1. Undefined, and not counted, in a seed in which either agent keeps quorum; not judged for a
  connectome on which no seed has both losses.

Reported for every connectome and agent, without a verdict: the loss concentration under each of the three rules; the
share of anatomical connections counting at the loss under the primary rule; the share of populations in the giant
component at three times the EC50 under each rule; the loss concentration of the coherence criterion; awake global
coherence; and the run time.

#### What we expect, stated before the run

- T2b-1 should pass on the human connectome. This is the prediction of the post hoc diagnostic above (a giant
  component of 0.10 at three times the EC50 with one draw per fibre, in the static estimate), now tested in the phase
  model on fresh seeds. Under the
  either-direction rule the human connectome should again keep quorum up to three times the EC50, as in C.12, and the
  both-directions rule should lose it earliest. If T2b-1 fails, timing variability does not abolish quorum on the
  human connectome even with one chance per fibre, and C.12's conclusion holds under every rule considered here.
- T2a-1 should pass on all three connectomes, as T2a-D did (20 of 20, 6 of 6 and 20 of 20 seeds). Because the giant
  component under the primary rule is never larger than under C.12's rule, a seed that loses quorum under C.12's rule
  also loses it under the primary rule, at the same or a lower concentration, provided quorum holds while awake. It
  should: at the reference values about 38% of connections are timing-coherent while awake (Section 4.7), which leaves
  each population with about 9 (*C. elegans*), 14 (human) and 14 (*Drosophila*, on average) counting connections; in a random graph
  of that mean degree the giant component holds nearly every population. As limitation 25 says of T2a, this cannot fail by
  construction at the maximum transmission failure chosen.
- On *C. elegans* and *Drosophila*, T2a-1 and T2b-1 should pass as T2a-D and T2b-D did, for the same reason. The
  losses should come at the same concentration as under C.12's rule or below it: on *Drosophila*, where only 7.5% of
  connections are linked both ways (1.08 chances per connection in C.12), within about one step of it; on
  *C. elegans* (1.66 chances per connection) earlier than C.12's 1.52 and 1.21 times the EC50.
- SP1-1 should pass on *C. elegans* and *Drosophila*, as SP1 did (20 of 20 and 6 of 6): the readout counts
  connections, so where both agents lose quorum the loss should sit at a common share of counting connections. On the
  human connectome SP1 could not be run in C.12, since no seed lost quorum under the NMDA-antagonist-like agent; with
  the primary rule it becomes evaluable, and its outcome is uncertain.
- What would change the reading of P4(b). If T2b-1 passes on the human connectome while the either-direction rule
  keeps quorum there, P4(b) holds on all three connectomes in this model only if a diffusion-MRI fibre counts once,
  and its human verdict depends on the reciprocity of human cortical connections, which diffusion imaging cannot
  measure. The paper will then report both verdicts and state that dependence; it will not report the human failure
  of C.12 as resolved.

#### Commands

From `simulator/`: the post hoc diagnostic, `../.venv/bin/python pair_rule_diagnostic.py` (about 15 seconds); the unit tests, `../.venv/bin/python -m unittest discover -s tests -t .`; a check that the code
runs end to end in seconds, `../.venv/bin/python dpc_pair_rule_study.py --smoke` (*C. elegans* only, one seed, two
concentrations, the shortest integration); the full study, `../.venv/bin/python dpc_pair_rule_study.py`. The report is
written to `simulator/results/dpc_pair_rule_full_<start time>.md` and `.json`; smoke reports (`_quick_`) are ignored by
git and are not results. From the run times of C.12's agent block and the measured cost of the added readings, the
full study should take about two and a half hours on the machine that ran C.12, almost all of it on *Drosophila*.

---

Reference to add to the reference list:

Markov, N. T., Ercsey-Ravasz, M. M., Ribeiro Gomes, A. R., et al. (2014). A weighted and directed interareal
connectivity matrix for macaque cerebral cortex. *Cerebral Cortex*, 24(1), 17–36. https://doi.org/10.1093/cercor/bhs270
