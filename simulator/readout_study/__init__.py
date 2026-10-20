"""The pre-specified DPC readout study (Appendix C.12), one module per responsibility.

settings: seeds, organisms and every fixed value of the design. pass_rule: the one rule every test uses.
conditions: the experimental conditions. running: one seed with the DPC readout, and pairing of runs.
calibrated_values: choosing a value on calibration seeds. Test families: agents, static_baseline, transitions,
fluctuations, disconnection, phase_inertia, weaker_coupling. plans: the blocks of the study and their order.
report: the JSON and Markdown report. The command is simulator/dpc_readout_study.py.
"""
