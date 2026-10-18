# Pre-revision results (17 October 2026)

These reports come from the first complete run of every study, made with the model as it stood
before the internal review of 17-18 October 2026. They are kept so that the model revision
described in the paper (Appendix D, "Model revision") can be checked against the original numbers.

They are superseded by the reports in `simulator/results/`. The main changes made after this run:

- independent timing errors combined in quadrature instead of added;
- baseline jitter set to the measured in vivo cortical value (3 ms; Buracas et al., 1998) instead of 1 ms;
- the reference feedback λ recalibrated to the same published inertia ratios;
- sleep down-states silencing whole populations, with connection-level silencing kept as an alternative;
- timing jitter in the phase model persisting for a correlation time instead of being redrawn every step;
- a degree-preserving rewired null model, directed quorum thresholds, Wilson confidence intervals,
  and labels separating tests from consistency checks.

Do not cite these numbers as results of the model.
