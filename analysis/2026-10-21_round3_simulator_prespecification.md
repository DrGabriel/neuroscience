# Pre-specification draft: the simulator analyses of the third round of review

Draft of 21 October 2026, for the authors to review, commit and then paste into Appendix C (as C.14) before any of the
four analyses is run in full. Nothing below has been run in full. The code was checked with unit tests and with one
smoke run of each command (`--smoke`), whose outcomes are listed under "What had been seen". The full runs are to be
launched by the lead author only after the code and this text are committed. Two new entries for the reference list
are given at the end.

---

### C.14 Pre-specified analyses requested in the third round of review

The four analyses below, their conditions, seeds and pass rules, or the statement that an analysis is reported
without a verdict, were written and committed before any of them was run in full. The code is
`simulator/prediction15_study.py` (analysis A), `simulator/directed_threshold_estimate.py` (B),
`simulator/reciprocity_estimate.py` (C) and `simulator/fresh_seed_validation.py` (D), with the package
`simulator/round3_study/`; the unit tests are `simulator/tests/test_round3_pulse.py` and
`simulator/tests/test_round3_estimates.py`.

**What these analyses are, and what they are not.** Referees asked for all four after the results of Appendices C.12,
C.13 and E.14 had been seen. They are therefore post hoc in origin, even though each is fixed here before its own run,
and none of them is a blind test of DPC. Analyses A and D ask whether the percolation model has properties the paper
attributes to it; analyses B and C are a deterministic computation and a static estimate, reported without a verdict.
No verdict reported earlier is changed by them.

**What had been seen.** Before this text was written we had read every report cited in Appendices B and C, including
the results of C.12, C.13 and E.14. The code was then checked with one smoke run per command. The first smoke runs
used the first seed of the blocks then intended for analyses A and D (the base seed plus 7000 and 7500, at 302 nodes)
and both generators then intended for C (7200 and 7201). Because their outcomes were read, those seeds were withdrawn
and every block was moved to offsets that no run has used (below); smoke runs now use a block of their own, the base
seed plus 7900 and 7901, which no analysis uses. What the smoke runs showed, on one seed or one draw each:

- A, at 302 nodes: on the withdrawn seed the window was one grid step wide (c_on 0.88, c_off 0.89) and both checks held;
  on the smoke seed it was 0.86 to 0.93, both checks held, and the smallest effective increases of the arousal drive
  were 0.061 inside the window and 0.368 above c_off.
- B is deterministic, so its smoke run computed the *C. elegans* row exactly: onset 0.0377, quorum estimate 0.0967,
  against 0.1058 measured in Appendix B.5. That row is known before the full run.
- C, with one assignment of direction and two draws: a giant component of 0.66 to 0.68 with every fibre two-way and
  0.07 to 0.13 with every fibre one-way, and 0.66 to 0.67 at the reference timing error. These agree with the post hoc
  diagnostic of Appendix C.13 (0.66 under the either-direction rule, 0.10 with one draw per fibre).
- D, at 302 nodes: on the withdrawn seed every claim held except C4; on the smoke seed every claim held, with a
  loss-to-recovery ratio of 1.081.

#### Seeds

Earlier studies used the base seed (20,261,017) plus 0 to 19, 1000, 2000, 3000, 4000, 5000, 5500, 5600 and 6000, each
block at most 20 seeds long. The seeds of this appendix are:

| Analysis | Seeds (offset from the base seed) | Count |
|---|---|---|
| A, prediction 15 | 7100 to 7119, at each network size | 20 per size, as in B.4 |
| C, reciprocity and timing error | 7300 (reciprocity sweep) and 7301 (timing-error sweep), one generator each | 2 |
| D, validation on fresh seeds | 7600 to 7619, at each network size | 20 per size, as in B.4 |
| Smoke runs only | 7900 and 7901 | 2 |
| Withdrawn (seen in early smoke runs) | 7000, 7200, 7201, 7500 | 4 |

Analysis B uses no random numbers. A unit test checks that every block of this appendix is disjoint from every
earlier block, from the withdrawn seeds, from the smoke block and from the others, and in particular that D's seeds
include none of the calibration seeds of `calibrate_feedback.py` and none of B.4's.

#### A. Prediction 15 in the percolation model

**Why.** Section 5.4 derives prediction 15 from P5 and P7: between the recovery and loss concentrations, where the
percolation model has two stable states, a brief arousing stimulus should restore quorum that outlasts it, and above
the loss concentration quorum should return only while the stimulus lasts. The section states that this follows from
the model's equation and has not been simulated. A referee asked for the simulation, and for the width of the window
in which the prediction applies, since an experiment has to hold the concentration inside it.

**Model and procedure.** The percolation model of Appendix B with every reference value (random graph of mean degree
8, GABAergic-like agent, $W$ = 3 ms, baseline jitter 3 ms, arousal level $A_0$ = 0.5, $\lambda$ = 8.85 ms, $q^*$ = 0.5,
concentration grid 0 to 3 times the EC50 in steps of 0.01), at the five network sizes of B.4 (302, 1,000, 10,000,
100,000 and 1,000,000 nodes), 20 seeds each. For each seed:

1. The reference sweep of B.4 gives the loss concentration $c_{\text{off}}$ (the last concentration of induction with
   quorum) and the recovery concentration $c_{\text{on}}$ (the highest concentration of emergence with quorum). The
   window is $[c_{\text{on}}, c_{\text{off}}]$; a seed without both, or with $c_{\text{off}} \le c_{\text{on}}$, has no
   window.
2. Two test concentrations are fixed from the seed's own window: (i) its midpoint, $(c_{\text{on}} + c_{\text{off}})/2$;
   (ii) $c_{\text{off}}$ + 0.1 times the EC50. The value 0.1 was chosen before any run of this analysis because it lies
   above $c_{\text{off}}$ in every seed and, in every seed of B.4 at every size, below the loss concentration of the
   model without feedback ($\lambda$ = 0), which is the state the full pulse produces (below): B.4's no-feedback loss
   exceeded $c_{\text{off}}$ + 0.1 by at least 0.02 EC50 in every seed.
3. The starting state is the unconscious state that induction leaves: the network is taken up the induction branch to
   three times the EC50, where quorum is lost, then set to the test concentration and settled there by the reference
   solver. This is the state on the emergence branch, the one an animal is in when it is stimulated during emergence.
4. The model has no time other than the steps of its self-consistency map, $S \to F(\pi(c, S))$. The pulse raises the
   arousal drive $A(c)$ of Section 4.3 by a fixed amount, capped at 1, for 500 steps (the iteration limit within which
   the reference solver must converge, so that the network settles under the pulse); $A$ then returns to baseline and
   the map is iterated to its steady state by the reference solver. The primary pulse raises $A$ by 1, which takes it
   to its maximum at every concentration: during the pulse the reference does not weaken ($\sigma_{\text{ref}}$ = 0),
   the strongest stimulus the model can represent. The secondary pulse raises $A$ by $A_0$ = 0.5, which brings the drive
   back at least to its awake value at every concentration, since the agent removes at most $A_0$.
5. Quorum before the pulse, at its end and after it is read against $q^*$ = 0.5.

**Checks.** Both are consistency checks, not tests, for a reason found while the code was written. With the primary
pulse the pulsed map does not depend on $S$, so one step takes the network to the state of the model without feedback.
Because the map is monotone in $S$ and in $A$, that state lies at or above the conscious branch wherever the conscious
branch exists, so after the pulse the network settles on it (P15a); above $c_{\text{off}}$ no state with quorum exists,
so after any pulse the network returns below $q^*$ (P15b). P15a can fail only where the window is too narrow for the
starting state to lie below $q^*$ at its midpoint, and P15b only where the model without feedback has already lost
quorum at $c_{\text{off}}$ + 0.1. The checks confirm that the code implements the equations; they do not test them.

- P15a (consistency check): inside the window, at its midpoint, the network starts without quorum, the primary pulse
  restores quorum, and quorum persists after the pulse.
- P15b (consistency check): at $c_{\text{off}}$ + 0.1 EC50, the network starts without quorum, the primary pulse restores
  quorum, and quorum is lost again after the pulse.

A seed without a window counts as failing both.

**Pass rule.** Appendix C.12's: a check passes at a network size when the lower bound of the Wilson 95% interval for
the share of seeds in which it holds lies above one half (15 of 20 seeds pass, 14 do not). There are two checks per
size and no correction for multiple comparisons.

**Reported without a verdict.** P15a and P15b with the secondary pulse ($A$ raised by 0.5); whether each seed has a
window; at each size, the mean and SD across seeds of $c_{\text{off}}$, $c_{\text{on}}$, the window width
$c_{\text{off}} - c_{\text{on}}$ in EC50, its midpoint, and the precision an experiment would need, half the width as a
share of the midpoint (aiming at the midpoint, the concentration must stay within that share of its target to remain
inside the window); the giant component before, at the end of and after each pulse and the first step of the pulse at
which quorum returned; and, by bisection on the increase of $A$ to 1/1024, the smallest increase that leaves quorum
persisting at the window's midpoint and the smallest that restores quorum during the pulse at $c_{\text{off}}$ + 0.1.
These two are the informative quantities: they say how strong an arousing stimulus must be, in the model's units, which
the checks do not.

**What we expect, stated before the run.**

- P15a and P15b should pass at every size, for the reason given under Checks. In B.4 one window, at 1,000 nodes, was one
  grid step wide, and the no-feedback loss lay above $c_{\text{off}}$ + 0.1 in every seed, so failures, if any, should
  be confined to a few seeds at 302 or 1,000 nodes.
- The window should be about as wide as B.4's hysteresis: 0.085 ± 0.037, 0.069 ± 0.041, 0.061 ± 0.013,
  0.061 ± 0.010 and 0.054 ± 0.005 EC50 from 302 to 1,000,000 nodes, around a midpoint near 0.86 EC50. An experiment
  would then have to hold the concentration within about 5% of its target in small networks and about 3% at
  1,000,000 nodes. This width belongs to random graphs of mean degree 8 with $\lambda$ calibrated to the inertia ratio
  1.08; on the connectome graphs of C.12 the calibrated $\lambda$ differs, and the window there is not computed here.
- The secondary pulse should restore quorum at the midpoint in every seed and leave it persisting, since at the
  midpoint the conscious branch exists and the drive is restored above its awake value. At $c_{\text{off}}$ + 0.1 it is
  marginal: a mean-field estimate for a random graph of mean degree 8 gives a giant component of about 0.6 during the
  pulse, so P15b with the secondary pulse may fail in some seeds because quorum does not return, not because it
  persists.
- The smallest increase at the midpoint depends on where the midpoint sits relative to $c_{\text{on}}$ and should be
  small; the smallest increase that restores quorum during the pulse above $c_{\text{off}}$ should be several times
  larger.

#### B. Directed generating-function estimate of the strong component

**Why.** Appendix B.5 measured the quorum threshold of each connectome on its directed wiring, as the occupation at
which the largest strongly connected component reaches $q^*$, and compared the undirected measurement with the
generating-function formula of Callaway et al. (2000), which it matched within 6%. A referee asked whether the directed
measurement also has a theoretical counterpart.

**Method.** For an uncorrelated directed network with joint distribution $p_{jk}$ of in-degree $j$ and out-degree $k$,
each arc kept with probability $\pi$ (Newman, Strogatz and Watts, 2001; Dorogovtsev, Mendes and Samukhin, 2001):

$$
\pi_c = \frac{\langle k \rangle}{\langle j k \rangle}, \qquad
x = 1 - \pi + \frac{\pi}{\langle k \rangle} \sum_{jk} p_{jk}\, j\, x^{k}, \qquad
y = 1 - \pi + \frac{\pi}{\langle k \rangle} \sum_{jk} p_{jk}\, k\, y^{j}, \qquad
S_{\text{strong}} = \sum_{jk} p_{jk} \bigl(1 - x^{k}\bigr)\bigl(1 - y^{j}\bigr),
$$

where $x$ is the probability that an arc does not lead into the giant out-component and $y$ that it does not come from
the giant in-component, each the smallest solution in [0, 1], found by iteration from zero. $\pi_c$ is the onset of a
giant strongly connected component, and the quorum estimate is the smallest $\pi$ at which $S_{\text{strong}}$ reaches
$q^*$ = 0.5, by bisection to about $10^{-12}$. Each population keeps its own pair $(j, k)$; every arc counts, as in B.5's
measurement, so a repeated arc is a second chance; self-connections are left out (there are none in the three
connectomes). The estimates are computed for *C. elegans*, *Drosophila* and the human connectome and set beside the
directed thresholds measured in B.5 (`simulator/results/percolation_full_20261020T011339Z.json`: 0.1058 ± 0.0079,
0.1503 ± 0.0006 and 0.0495 ± 0.0015), with the critical transmission failure and timing error they imply, as in B.5.

**Reported without a verdict.** The computation is deterministic. The estimate assumes an uncorrelated network, so it
ignores every correlation between populations, among them reciprocity (46% of *C. elegans* connections and 7.5% of
*Drosophila* connections are two-way, Appendix C.13, and every human connection is), degree assortativity and
modularity. A difference from the measurement measures how much those correlations matter; it does not test DPC.

**What we expect, stated before the run.** The *C. elegans* row is known from the smoke run: the estimate, 0.0967, is
9% below the measurement. For the human connectome, in which every population has as many inputs as outputs,
$\pi_c = \langle k \rangle / \langle k^2 \rangle$ = 35.8 / 1,536.3 = 0.0233 from B.5's degree moments, close to the
undirected onset of 0.0239. Reciprocity creates two-arc cycles that an uncorrelated network lacks, which should lower
the measured threshold below the estimate, while modularity and the other correlations can move it either way; *C.
elegans* moved the other way. We therefore state no expectation for the direction of the difference on *Drosophila*
or the human connectome, and expect agreement within about 20%, as the undirected formula agreed within 6%.

#### C. Static estimates of reciprocity and maximal timing error on the human connectome

**Why.** Appendix C.13 showed that the human verdict of clause (b) of P4 depends on how a connection inferred from
diffusion MRI is counted: with every fibre two-way and either direction sufficient, timing variability alone does not
abolish quorum; with one timing draw per fibre, it does. Diffusion MRI cannot say how many human fibres are two-way. A
referee asked how much reciprocity the either-direction result needs, and how large the agent's timing error must be
before even a fully reciprocal connectome loses quorum.

**Method.** Static, as the diagnostic of C.13 (`pair_rule_diagnostic.py`): no oscillators run, and every arc is on time
independently with the probability of C.12's static baseline at three times the EC50 of the NMDA-antagonist-like
agent, $(1 - p)\,\operatorname{erf}(W / (2\sqrt{2}\,\sigma_{\text{eff}}))$, with $\sigma_{\text{eff}}$ combining the
baseline jitter and the agent's added error (0.024 at its reference maximal error of 40 ms). The giant component is
read under C.12's either-direction rule: a fibre counts when any of its arcs is on time.

- (i) Reciprocity sweep. For each reciprocal share $r$ from 0 to 1 in steps of 0.05, a random share $r$ of the 17,865
  human fibres is made two-way and the rest one-way in a random direction (each direction with probability one half);
  the number of fibres never changes. Ten assignments of direction per value of $r$, 20 timing draws on each.
- (ii) Timing-error sweep. With every fibre two-way ($r$ = 1), the agent's maximal added timing error is set to 20, 25,
  ..., 80 ms (its reference value is 40 ms), ten assignments of 20 draws each.

For each sweep, the mean giant component (over assignments and draws) is reported at every value, and the value at which
it first falls below $q^*$ = 0.5 is interpolated linearly between the two grid values around the crossing, reading $r$
downwards from 1 and the timing error upwards from 20 ms. A sweep that never crosses is reported as such.

**Reported without a verdict.** These are post hoc static estimates requested by referees. They leave out the
oscillator dynamics, which in C.12 did not reliably bring the timing loss forward (T0b-D), and they assume that the two
directions of a fibre are timed independently, an upper bound on the benefit of reciprocity.

**What we expect, stated before the run.** Under the either-direction rule with independent arcs, a fibre counts with
probability $p + r\,p(1 - p)$, and the direction of a one-way fibre does not matter, so sweep (i) is bond percolation
on the undirected human graph at that occupation. Setting it equal to B.5's undirected quorum threshold (0.0368 by
formula, 0.0381 measured) gives a crossing at $r$ of about 0.53 to 0.59: quorum should survive the timing faults only
if more than about half of the human fibres are two-way. For sweep (ii), $2p - p^2$ reaches the same thresholds when the
maximal added timing error is about 50 to 52 ms, so a fully reciprocal human connectome should keep quorum at three
times the EC50 unless the agent's maximal timing error exceeds about 50 ms, a quarter more than the 40 ms assumed.

#### D. The validation study on seeds disjoint from calibration and from B.4

**Why.** Appendix C.12 found that the percolation feedback was calibrated (`calibrate_feedback.py`) on the base seed
plus 0 to 9 at 10,000 nodes, and that B.4 used the base seed plus 0 to 19 at every size with the same graph builder,
so ten of B.4's twenty networks at 10,000 nodes were the calibration networks themselves. A referee asked for the
validation to be repeated on networks that played no part in calibration.

**Method.** `validation_study.py` unchanged, with every claim (C1 to C7), observation (O1 to O5) and extension test
(E1 to E3) of B.4, at B.4's five sizes with 20 seeds each, on the base seed plus 7600 to 7619. The calibrated $\lambda$
is not recalibrated. Also reported, without a verdict, at every size: the loss-to-recovery concentration ratio
$c_{\text{off}} / c_{\text{on}}$ of the reference sweep (mean ± SD across seeds) and the number of seeds in which it lies
within the published range of 1.07 to 1.63.

**Pass rule.** B.4's: a claim holds at a size only when it holds in every seed, and the verdict is that every claim
holds at every size, or that at least one failed. Observations and extension tests are reported, not judged.

**What we expect, stated before the run.** The code and design are B.4's, so B.4's outcomes should recur. C1 to C3 and
C5 to C7 held in every seed at every size and should hold again. C4 held in 19 of 20 seeds at 302 nodes, so the
every-seed rule may fail again there for that reason alone, as it did in B.4. The ratio should fall with size, as in
B.4 (1.106 ± 0.050, 1.086 ± 0.055, 1.075 ± 0.017, 1.075 ± 0.013 and 1.066 ± 0.006 from 302 to 1,000,000 nodes, within
the published range in 14, 10, 14, 15 and 9 of 20 seeds). At 10,000 nodes B.4's calibration seeds gave 1.079 ± 0.015
and its other ten seeds 1.071 ± 0.019, so on fresh seeds the ratio should be near 1.07, slightly below the target of
1.08 to which $\lambda$ was calibrated, and near the lowest published ratio at 1,000,000 nodes. A ratio well below 1.07
on fresh seeds would show that the calibration fitted its own networks rather than the model.

#### Commands and run times

From `simulator/`: the unit tests, `../.venv/bin/python -m unittest discover -s tests -t .`; and for each analysis,
a check that the code runs end to end in about a second (`--smoke`, on the smoke seeds only) and the full run:

| Analysis | Full run | Estimated run time |
|---|---|---|
| A | `../.venv/bin/python prediction15_study.py` | about 2 minutes, at most 5 |
| B | `../.venv/bin/python directed_threshold_estimate.py` | under 1 minute |
| C | `../.venv/bin/python reciprocity_estimate.py` | under 1 minute |
| D | `../.venv/bin/python fresh_seed_validation.py` | about 12 minutes |

The estimates are for the machine that ran B.4 (Apple M2 Pro, 10 worker processes). D repeats B.4's design, which took
695.5 s. A needs one graph, one percolation curve and one sweep per seed, against about fifteen of each per seed in
B.4, whose seeds took 320 s each at 1,000,000 nodes, so about 25 s per seed there and about one minute for its 20
seeds on 10 workers; the pulses and bisections add about 13,000 steps of the map per seed, each a single lookup. B
needs about 8 s to load the *Drosophila* connectome, and its *C. elegans* row took under a second. C reads the giant
component about 6,800 times on the human connectome, at about 0.5 ms a reading and 1.4 ms per assignment of direction
as timed on that machine, about 5 s in all. Each report is written to `simulator/results/<kind>_full_<start time>.md`
and `.json`, with kinds `prediction15`, `directed_threshold_estimate`, `reciprocity_estimate` and
`validation_fresh_seeds`; smoke reports (`_quick_`) are ignored by git and are not results.

---

References to add (both cited in C.14 B):

Dorogovtsev, S. N., Mendes, J. F. F., & Samukhin, A. N. (2001). Giant strongly connected component of directed
networks. *Physical Review E*, 64(2), 025101. https://doi.org/10.1103/PhysRevE.64.025101

Newman, M. E. J., Strogatz, S. H., & Watts, D. J. (2001). Random graphs with arbitrary degree distributions and their
applications. *Physical Review E*, 64(2), 026118. https://doi.org/10.1103/PhysRevE.64.026118
