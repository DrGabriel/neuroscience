# Pre-specification draft: the phase-model results re-tested with a readout that implements P2 and P3

Draft of 21 October 2026, for the authors to review, commit and then paste into Appendix C (as C.12) before the full
study is run. Nothing below has been run in full. The code was checked with unit tests and with one shortened smoke
run (`--quick`); the expectations section says where a shortened probe informed them. The full study is to be
launched by the lead author only after the code and this text are committed.

---

### C.12 Pre-specified test of the connectome results with a DPC readout

The tests below, their conditions, seeds and pass rule were written into this paper and committed before the study
that evaluates them was run (`simulator/dpc_readout_study.py`, with `simulator/dpc_readout.py` and
`simulator/connectome_inertia.py`). Before that, the code was checked with unit tests and with one shortened run
(`--quick`: one seed per organism and condition, a quarter of the settling time and about an eighth of the
measurement time). Its outcomes were computed and read while the code was checked; with one seed per condition and
shortened integration they are not part of the results.

**Why this study.** A hostile review found, and we confirmed, that the phase-oscillator model behind every connectome
result in this appendix implements neither P2 nor P3. A timing error weakens a connection's coupling smoothly (by
the factor $e^{-s^2/2}$, Section 4.5), the integration window $W$ is never used, and quorum is defined as global
coherence at least half its awake value (`InductionEmergenceRecord.is_conscious` in `simulator/phase_dynamics.py`).
The same review found three further problems. The shared reference of P5 pulls every population towards the phase of
the global mean field with no transmission failure, no timing error and no connections, so neither fault reaches the
reference, and the model is effectively mean-field, which may be why the rewired null models matched the real
wiring. The awake network is close to full synchrony (global coherence 0.93, 0.88 and 0.96 on *C. elegans*,
*Drosophila* and the human connectome). And the percolation model's feedback $\lambda$ was calibrated and its inertia
tested only on random graphs of mean degree 8. The results of Appendices C.3 to C.11 therefore show that oscillator
synchrony is lost under the two agents, which any coupled-oscillator model would show; they do not test whether
timing-coherent connections stop forming a quorum. This study reads the same simulations as P2 and P3 are worded,
adds the missing conditions, and repeats the main tests on fresh seeds.

#### The DPC readout

The dynamics are unchanged: the readout only looks at quantities the model already computes. A unit test checks that
every measurement of a sweep is identical, to the last bit, with and without it, and the reference model's dynamics
were checked to be identical, to the last bit, to those of the code that produced Appendices C.3 to C.11.

- *Timing error (P2).* At a sampled moment, a connection $j \to i$ that transmits ($m_{ji} = 1$) carries a signal
  whose timing error relative to the shared rhythm is, in radians of the reference cycle,
  $\delta_{ji} = \operatorname{wrap}(\theta_j - \psi) - \alpha_{ji}$, where $\theta_j$ is the phase of the sending
  population, $\psi$ the phase of the network's mean rhythm, $\alpha_{ji}$ the connection's phase error in that same
  integration step (conduction lag, zero here, plus its current jitter draw, the same $\alpha_{ji}$ that enters the
  coupling term), and $\operatorname{wrap}$ maps an angle to $[-\pi, \pi)$. A population can lead or lag the rhythm by
  at most half a cycle, so its offset is wrapped; the delay error is not, so a signal a whole cycle late is late, as
  in the percolation model and as P2 states ("signals outside the window are not integrated").
- *Counting connection.* The connection counts in that cycle when it transmits and $|\delta_{ji}| \le W/2$, with $W$ =
  3 ms converted to phase at the reference rate in force ($\pi f W$ either side; 0.377 rad at 40 Hz).
- *Quorum (P3).* In each sampled cycle the counting connections are taken as undirected links, as in the percolation
  model, and the share of populations in their largest connected component is computed; a population with no
  counting connection is a component of one. Quorum holds in the cycle when that share is at least $q^*$ = 0.5.
- *Cycles.* The model's time is dimensionless: only timing errors are converted from milliseconds to phase, so the
  model does not fix how many time units one 25 ms cycle lasts. One cycle is sampled per jitter correlation time
  $\tau$, the time over which a connection's timing error renews, so that successive cycles see largely fresh errors;
  if one time unit is read as one reference cycle, which puts the natural-frequency spread of 0.5 at about 3 Hz, this
  is also one sample per cycle. The measurement window of 838 steps of 0.05 gives 42 cycles at each concentration
  (168 with the eight-cycle window of K1d and K1e).
- *Quorum at a concentration.* Quorum holds at a concentration when it holds in at least half its cycles. The DPC loss
  concentration is the last concentration of induction at which it holds before it is first lost, and the DPC
  recovery concentration the highest concentration of emergence at which it has returned, as for the coherence
  criterion.
- *Static baseline.* With awake coherence near 0.96 the populations sit close to the rhythm, so the readout could
  largely reproduce the static percolation draw. Two baselines are therefore recorded at every concentration: the
  analytic prediction of Section 4.1, $\pi(c) = (1 - p(c))\operatorname{erf}(W / (2\sqrt 2\,\sigma_{\text{eff}}))$,
  evaluated for each transmitting connection with its own timing error and summed over all connections; and a
  *static reading*, the same giant-component readout with $\delta_{ji} = -\alpha_{ji}$, that is, static bond
  percolation on the model's own timing draws, ignoring how far each population has drifted from the rhythm. Tests
  T0a-D and T0b-D ask where the oscillator readout departs from the static one.
- *Secondary readings, reported without a verdict.* Timing measured at the receiver, with everything wrapped,
  $|\operatorname{wrap}(\theta_j - \theta_i - \alpha_{ji})| \le \pi f W$: the quantity whose sine the coupling term
  takes (communication through coherence); because $\alpha_{ji}$ is wrapped, an error far beyond a cycle leaves a
  chance floor of $W f$ (12%) of transmitting connections counting. And the largest strongly connected component of
  the directed counting connections, reported only for *C. elegans* and *Drosophila*: the human connectome is
  structurally symmetric (its 35,730 arcs are its 17,865 undirected links in both directions, since diffusion imaging
  gives no direction), so it enters no directed analysis. P2's wording ("relative to a shared phase reference") and
  Section 4.1 favour the shared rhythm, which is therefore primary. The coherence criterion is also reported for every
  run, for comparison.
- *Coupling left at each concentration.* The synaptic effective coupling
  $K_{\text{eff}} = K \sum_{\text{transmitting}} |w_{ji}|\, e^{-s_{ji}^2/2} / \sum_{\text{all}} |w_{ji}|$, with $s_{ji}$
  the connection's phase-error SD (the mean-field factor by which Gaussian timing error weakens sine coupling; a fixed
  lag only shifts the phase and is ignored), and the coherence-dependent strength of the reference, $\lambda_{\text{osc}}
  (1 - A(c))$. They are compared with the critical coupling of the all-to-all Kuramoto model with Gaussian natural
  frequencies of SD $\sigma$ and phase noise of intensity $D$ (Strogatz and Mirollo, 1991),
  $K_c = 2 / \int g(\omega)\, D / (D^2 + \omega^2)\, d\omega = 2\sigma\sqrt{2\pi} / (\pi \operatorname{erfcx}(D / (\sigma\sqrt 2)))$,
  which without noise is Kuramoto's $\sigma\sqrt{8/\pi}$ (Kuramoto, 1984): 0.798 without noise and 0.863 with the
  model's $D$ = 0.05 for $\sigma$ = 0.5. The formula assumes all-to-all coupling, infinitely many oscillators and
  unimodal frequencies; the connectomes are sparse and finite, so $K_c$ is a reference value, not the model's own
  threshold.

#### New conditions

- *Reference carried by the connections (referee point 3).* Each population's reference is the mean phase of the
  signals arriving from its transmitting inputs, $R_i e^{i\psi_i} = \sum_j w_{ji} m_{ji} e^{i(\theta_j - \alpha_{ji})} / s_i$,
  with the same failures $m_{ji}$ and phase errors $\alpha_{ji}$ as the synaptic term in the same step and the same
  intact in-strength $s_i$, so that failures weaken the reference as they weaken coupling. Its pull keeps the
  reference model's form, $\lambda_{\text{osc}}[R_i + A(c)(1 - R_i)]\sin(\psi_i - \theta_i)$, so the arousal share is kept;
  a population with no transmitting input receives none. The global reference is kept as the comparison condition,
  and every earlier study keeps it by default.
- *Weaker coupling (referee point 4).* Target, fixed before any run: awake global coherence between 0.5 and 0.7. For
  each connectome, the GABAergic-like condition is held at zero concentration only, with the synaptic coupling $K$ =
  0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5 and 3, on 4 calibration seeds (from the base seed plus 5600); the chosen $K$ is
  the one whose mean awake coherence lies in the target range and closest to 0.6. If none does, the connectome is
  reported as not calibrated and its weaker-coupling tests are not run.

#### Seeds

Every test uses seeds that no earlier run used, from the base seed plus 5000: 20 for *C. elegans*, 6 for
*Drosophila* and 20 for the human connectome in the phase model, and 20 for each connectome in the percolation
model. Calibrations use separate fresh blocks: the phase-model feedback scan and the percolation-model calibration
from the base seed plus 5500 (10 seeds each), the weaker coupling from the base seed plus 5600 (4 seeds). Every
calibrated value is tested on the first block only, so no seed both calibrates and tests a value. Checking the earlier
studies for this found two overlaps. The percolation feedback was calibrated (`calibrate_feedback.py`) on the base
seed plus 0 to 9 at 10,000 nodes, and the validation study (`validation_study.py`) uses the base seed plus 0 to 19 at
every size, including 10,000 nodes, with the same graph builder: 10 of its 20 seeds at that size are the calibration
networks themselves. The oscillator calibration (`calibrate_phase_feedback.py`) used the base seed plus 0 to 3 on the
human connectome, which are also the first four human seeds of the cross-species study. Neither overlap changes a
verdict reported above, but the validation at 10,000 nodes is not independent of the calibration.

#### Pass rule

One rule for every test: a test passes for an organism when the lower bound of the Wilson 95% interval (Wilson,
1927) for the share of seeds in which it holds lies above one half. We prefer it to the 80% rule of the earlier
studies because it is a statement about the model's realisations (most of them, with 95% confidence) and because it
is stricter where seeds are few: 15 of 20, 9 of 10 and 6 of 6 seeds pass; 14 of 20, 8 of 10 and 5 of 6 do not. With 20
seeds it is slightly weaker than the 80% rule (15 rather than 16 seeds). Seeds are realisations of one wiring
diagram, not independent brains (Section 10, item 28), and no correction for multiple comparisons is made; this study
has about 30 tests per connectome.

Every other parameter keeps its reference value (Appendix C.1); concentrations run from 0 to 3 times the EC50 in
steps of 0.05 (0.1 for *Drosophila*) in the phase model and 0.01 in the percolation model. A seed in which DPC quorum
does not hold even at zero concentration counts as failing every test that needs a loss.

#### Tests: agents, null model and the wired reference

Conditions: the GABAergic-like and the NMDA-antagonist-like agent on the three connectomes, each with the global
reference and with the reference carried by the connections; and all four on degree-preserving rewired copies of
the *C. elegans* and human connectomes (Maslov and Sneppen, 2002), one rewiring per seed. The fly's null model is not
run, as before, for cost.

- T2a-D, T2b-D: the GABAergic-like (T2a-D) and NMDA-antagonist-like (T2b-D) agent abolishes DPC quorum within the
  concentration range (a DPC loss concentration exists).
- T2a-DN, T2b-DN (null model): the same on the rewired connectomes.
- W2a, W2b: the same with the reference carried by the connections.
- WNa, WNb (wiring, paired by seed): with the reference carried by the connections, the DPC loss concentration on the
  connectome and on its rewired copy differ by more than one concentration step (a seed in which only one of them
  loses quorum counts as differing). GNa, GNb: the same comparison with the global reference.

#### Tests: where the readout departs from static percolation, and what kind of transition the loss is

- T0a-D, T0b-D: under each agent (global reference), DPC quorum is lost at a lower concentration than the static
  reading on the same timing draws loses it, or the static reading never loses it. A pass means that the populations'
  drift from the rhythm, not the timing draws alone, decides where quorum is lost. Reported alongside, without a
  verdict: the share of counting connections over the analytic $\pi(c)$ at the DPC loss.
- SP1 (paired by seed, per connectome): at their DPC losses the two agents leave more similar shares of counting
  connections than effective couplings $K_{\text{eff}}$, compared as absolute log ratios. This is what a percolation
  transition predicts: the same share of counting connections, however it is reached.
- SP2 (paired by seed, per connectome): at their coherence-criterion losses the two agents leave more similar
  effective couplings than shares of counting connections. This is what a synchronisation transition predicts.
- Reported without a verdict: $K_{\text{eff}} / K_c$ at both losses on every connectome, which shows whether the
  coherence loss happens near a common effective coupling across connectomes.

#### Tests: fluctuations at the threshold (T1d, T1e, T1f)

Condition: the GABAergic-like agent with the global reference. The threshold is the last concentration with DPC
quorum. T1b compared the susceptibility $N\,\mathrm{var}(R)$ there with its awake value, but $N\,\mathrm{var}(R)$ rises
whenever coherence falls, even for independent phases, so a rise from the awake level does not show collective
fluctuations. T1d compares it instead with what independent phases with the same mean coherence and the same spread
around the rhythm would give,
$\chi_{\text{ind}} = \tfrac{1}{2}\bigl(1 + \langle\cos 2(\theta - \psi)\rangle\bigr) - \langle R\rangle^2$, the
variance of one population's projection on the mean rhythm; the ratio $\chi / \chi_{\text{ind}}$ is about 1 plus
$N - 1$ times the mean correlation between populations' fluctuations, and equals 1 for independent phases. The
approximation holds while $\langle R\rangle$ is well above chance ($1/\sqrt N$).

- T1d: at the threshold, $\chi / \chi_{\text{ind}} \ge 2$.
- T1e: at the threshold, the autocorrelation of global coherence $R$ at a lag of one sampled cycle is higher than at
  zero concentration (critical slowing down; Scheffer et al., 2009).
- T1f (finite size): for the same seed, $\chi / \chi_{\text{ind}}$ at the threshold is larger on the human connectome
  (998 populations) than on *C. elegans* (300), and larger on *Drosophila* (138,639) than on the human connectome;
  evaluated for each pair of neighbouring sizes, under the larger connectome.

A seed without a DPC threshold, or with an undefined quantity, counts as failing. T1b is reported again on these seeds
without a verdict.

#### Tests: weaker coupling (T2a-M, T2b-M)

On each calibrated connectome, at its calibrated $K$: the GABAergic-like (T2a-M) and NMDA-antagonist-like (T2b-M)
agent abolishes DPC quorum within the concentration range. Awake global coherence is reported for every seed.

#### Tests: sensory disconnection with its control (K1d, K1e)

Conditions: those of K1c (Appendix C.11): the NMDA-antagonist-like agent adds its timing error only on connections
leaving the sensory populations, a sensory stimulus is applied, broadcast is measured over eight stimulus cycles, and
each seed is run with the stimulus and with a phantom of zero strength. The control repeats both with the agent's
timing error on as many connections drawn at random for each seed (460 of 5,764 in *C. elegans*, 267 of 35,730 in the
human connectome), from a random stream of their own. The awake gate and the evaluability rule are K1c's: a seed is
applicable only if its awake locking to the stimulus is at least twice its awake locking to the phantom, and a test is
judged for an organism only if at least half its seeds are applicable.

- K1d: in an applicable seed, DPC quorum holds at the highest concentration (three times the EC50) and the broadcast
  above the floor there is at most half the awake broadcast above the floor.
- K1e (control, paired by seed; applicable when both the sensory and the random runs pass the gate): K1d holds with
  the error on the sensory pathways and does not hold with it on as many random connections. Without K1e, a pass of
  K1 or K1c could come from construction alone: faults on a minority of connections leave quorum intact, and the
  stimulus may stop spreading for reasons unrelated to where they fall.

#### Tests: neural inertia in the phase model (I1, I2)

The reference term $\lambda_{\text{osc}} R \sin(\psi - \theta_i)$ is all-to-all Kuramoto coupling of strength
$\lambda_{\text{osc}}$, so its locking threshold is $K_c$ = 0.863 above. The calibration of Appendix C.2 stopped at
0.75, below it. Conditions: the GABAergic-like agent with $\lambda_{\text{osc}}$ = 0, 0.5, 0.75, 1, 1.25 and 1.5 times
$K_c$ (0, 0.431, 0.647, 0.863, 1.078 and 1.294), on *C. elegans* and the human connectome, 10 seeds each from the
calibration block.

- I1 (at each scanned $\lambda_{\text{osc}}$): DPC quorum returns on emergence more than one concentration step below the
  concentration at which it was lost. Inertia in the DPC readout is supported if I1 passes at at least one scanned
  value; with six values per connectome, one pass could arise by chance.
- Calibration rule: for each connectome, among the scanned values at which every calibration seed loses DPC quorum
  and regains it above zero concentration, the value whose mean ratio of loss to recovery concentration is closest
  to the reference ratio of 1.08 (Friedman et al., 2010). If no value qualifies, the connectome is reported as not
  calibrated and I2 is not run for it.
- I2 (held-out, 20 seeds from the test block at the calibrated value): the seed's ratio of DPC loss to DPC recovery
  concentration lies within the measured range that the percolation model reproduces, 1.07 to 1.63.

#### Tests: neural inertia in the percolation model on the connectome graphs (PI1 to PI4)

The percolation model, with every reference parameter unchanged (arousal level 0.5, the GABAergic-like agent, $q^*$ =
0.5, $W$ = 3 ms, baseline jitter 3 ms), runs on the undirected graphs of the three connectomes
(`percolation_thresholds.undirected_graph`); each seed varies only the percolation draws. Calibration: on each of 10
calibration seeds, $\lambda$ is scanned from 0 to 30 ms in steps of 0.1 ms; for each measured ratio (1.07, 1.08,
1.11, 1.63), the chosen $\lambda$ is the scanned value at which every calibration seed loses quorum and regains it,
with the mean ratio closest to the target; the target counts as reproduced when that mean lies within 0.01 of it, as
in `calibrate_feedback.py`. Held-out tests, 20 seeds from the test block, at $\lambda$ = 0 and at each reproduced
target's $\lambda$:

- PI1: at the $\lambda$ calibrated to 1.08, quorum is lost and regained at a strictly lower concentration.
- PI2 (C3's form): the hysteresis width never shrinks along the series of calibrated $\lambda$ and is larger at its end
  than without feedback; never recovering counts as unbounded inertia.
- PI3 (C2's form, a consistency check): without feedback the hysteresis width is exactly zero.
- PI4: at the $\lambda$ calibrated to 1.08, the seed's ratio lies within 1.07 to 1.63.

PI1 and PI4 are not run for a connectome on which 1.08 is not reproduced; PI2 needs at least one reproduced target.

#### What we expect, stated before the run

Before the referee's latest points, we ran the readout once on one seed outside every block (seed 99, not derived
from the base seed) with shortened integration and a coarse grid of 0.25, to check that it works; the figures below
come from that probe and are a single realisation. No other run informed these expectations.

- T2a-D should pass on all three connectomes: up to 95% transmission failure removes counting connections however
  well the remaining ones are timed (in the probe, DPC quorum was lost at 1.5 to 1.75 times the EC50, one or two
  probe steps later than coherence). As limitation 25 says of T2a, this cannot fail by construction; what it adds is
  where the loss happens. T2a-DN and W2a should pass for the same reason.
- T2b-D may fail on the human connectome. Its connections are dense (a mean undirected degree of about 36), and at
  three times the EC50 about 2.4% of them still counted in the probe, enough for an undirected giant component of 65%
  of the populations. On *C. elegans* (mean undirected degree 23) the giant component fell to about 20% in the probe,
  so T2b-D should pass there. The fly is not predicted. A failure would mean that timing faults alone do not abolish
  quorum in a densely wired network as DPC states it, which bears on P4(b) and on assigning ketamine to timing faults.
- T0a-D and T0b-D are uncertain. With the populations close to the rhythm while awake, the oscillator readout should
  follow the static reading at low concentrations; whether it departs before the loss depends on how far the
  populations drift as coupling weakens. If both fail, the DPC readout of the phase model is static percolation on
  its timing draws, and the oscillators add nothing to the quorum result.
- SP1 should pass and SP2 may pass: the DPC readout counts connections, so its loss should sit at a common share of
  counting connections, while the coherence criterion is a synchronisation measure. If SP2 fails as well, the
  coherence loss is not set by the effective coupling either, and the two agents differ in more than coupling.
- WNa and WNb are the informative tests of the wired reference: if the global reference is why the null models matched
  the real wiring, GNa and GNb should fail and WNa or WNb pass. If all four fail, the match does not come from the
  reference.
- T1e should pass if the threshold behaves as a generic critical transition (in the probe, the lag autocorrelation
  was 0.93 at the threshold against about 0 awake on *C. elegans*). T1d is uncertain: in the probe the ratio at the
  *C. elegans* threshold was 2.2, just above the bar. T1f is uncertain, and its comparison is confounded: the three
  connectomes differ in wiring and density as well as size.
- T2a-M and T2b-M are uncertain. A weaker coupling leaves the populations further from the rhythm while awake, so
  fewer connections count; DPC quorum may already fail at zero concentration, which counts as failing.
- K1d should pass on *C. elegans*, where the sensory outputs are 8% of the connections, and is likely not evaluable on
  the human connectome, as K1c was. K1e is the informative test: if the broadcast collapse under K1 comes from the
  agent's uniform transmission failure and arousal suppression rather than from timing faults on the sensory
  pathways, K1e will fail, and the disconnection account of ketamine (Section 7.4) will lose its model support.
- I1 should fail at every value. For a unimodal distribution of natural frequencies, the onset of synchrony in the
  Kuramoto model is continuous, without the bistability that inertia needs (Kuramoto, 1984); above $K_c$ the
  reference alone can hold the populations in step, so the coherence criterion may never register a loss while DPC
  quorum is lost to transmission failure, the disagreement that a unit test
  (`test_in_the_model_a_strong_reference_keeps_coherence_after_dpc_quorum_is_lost_Regression`) shows on a small
  network. If I1 fails, the calibration will pick the value whose ratio is nearest 1.08 from below, and I2 will fail;
  that would extend limitation 9 to the DPC readout. A pass of I1 and I2 would be the first phase-model support for P5.
- PI1 to PI4 are uncertain. The percolation model reproduces the measured ratios on random graphs, and its inertia
  comes from the self-consistency of the giant component with the reference, which does not depend on the graph's
  degree distribution; but the connectome graphs are denser than mean degree 8, so the transition is sharper and the
  calibrated $\lambda$ may differ, or no $\lambda$ may let every seed recover. A failure of PI4 on held-out seeds would
  show that the calibration does not generalise across seeds on a fixed wiring diagram.

#### Commands

From `simulator/`: the unit tests, `../.venv/bin/python -m unittest discover -s tests -t .`; a check that the code
runs end to end in seconds, `../.venv/bin/python dpc_readout_study.py --smoke` (*C. elegans* only, one seed, two
concentrations, the shortest integration); a shortened run of every organism, `../.venv/bin/python
dpc_readout_study.py --quick`; the full study, `../.venv/bin/python dpc_readout_study.py`. The report is written to
`simulator/results/dpc_readout_full_<start time>.md` and `.json`; smoke and quick reports (`_quick_`) are ignored by
git and are not results.

---

## Notes for the authors (not for the appendix)

- Expected wall time of the full study, on the 10-core machine used for the earlier studies, estimated from the
  `--quick` run that the lead author stopped after 41 minutes (it shared the processor with another analysis) and
  scaled by the full study's 5 to 6 times more integration steps and 8 times more sampled cycles; treat it as within
  about a factor of 1.5. *C. elegans*: about 1 hour (quick: 8 agent runs in 6 seconds of wall time). Human
  connectome: about 4 hours (quick: about 50 seconds a run; the K1d and K1e runs measure over four times as long).
  *Drosophila*: about 15 hours (quick: about 24 minutes a run with the readout; full runs about 2.5 hours each, 24 agent
  runs and 12 weaker-coupling runs on 6 workers). Percolation model on the connectome graphs: about 1 hour, mostly the
  fly. In all, about 20 hours, two thirds of it the fly. Dropping the fly from the wired-reference and weaker-coupling
  conditions would save about 10 hours; that is the authors' decision, to make before committing.
- The `--smoke` run on the final code finished in 3.3 seconds and exercised every block except the weaker coupling
  and the held-out phase-model validation, which its two-concentration, 60-step runs cannot calibrate (no coupling
  reached the target coherence range and no feedback let the seed recover above zero); unit tests cover both paths.
- The readout is primary at the shared rhythm and the undirected component, as P2 and P3 are worded. If the authors
  prefer another reading as primary, change `ReadoutRun.dpc_loss_concentration` before committing, not after the run.
- The bar of 2 in T1d, the target range 0.5 to 0.7 for the weaker coupling and its grid are free choices; change
  `MATCHED_COHERENCE_EXCESS`, `METASTABLE_COHERENCE_RANGE` or `COUPLING_GRID` before committing if wanted.
- The probe used to state some expectations ran on seed 99, outside every block; quote it as a probe, or remove those
  sentences, if the authors prefer expectations stated without it.
- References to add to the paper's list if this text is adopted: Strogatz, S. H., and Mirollo, R. E. (1991).
  Stability of incoherence in a population of coupled oscillators. *Journal of Statistical Physics*, 63, 613-635. The
  statement that the Kuramoto onset is continuous for unimodal frequency distributions is attributed to Kuramoto
  (1984); please check it against the source before committing.
- No mutation testing or coverage measurement was run (no such tooling is installed in this repository).
