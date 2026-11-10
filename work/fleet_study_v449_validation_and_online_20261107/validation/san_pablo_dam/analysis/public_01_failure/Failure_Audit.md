# Public validation attempt 1: finite-horizon failure

The source-frozen day-1 tau=1.2 run returned 2,298 unique trip records. Of these, 2,179 arrived and 119 had arrival=-1. The terminal summary at 33,572 s independently reports loaded=inserted=2,298, running=119, arrived=ended=2,179, waiting=0, and collisions=teleports=discarded=0. Thus the failure is genuine terminal-horizon censoring, not a parser count error. The four scored detector populations had passed the complete-crossing check before the arrival assertion failed.

The attempt is retained as FAIL, with no candidate selection and no accepted calibration score. It must not be converted into a success by removing the 119 unfinished vehicles. No empirical validation or delivery-network calibration is claimed.

Root approved a single execution-horizon amendment, uniformly replacing last observed station-8 time plus 900 s with plus 7,200 s for every candidate and both days. Parameters, observations, QC, seeds, training selection, held-out evaluation and measurement code are unchanged. The extension was selected from terminal completeness evidence, without inspecting error scores. The 45-second process limit, 300-second total limit and full-arrival requirement remain; another incomplete result will be reported without further horizon tuning.

Version 2 has separate source/protocol/preparation files and a fresh output directory. The original shared helper and its preparation manifest remain unchanged for the online gate. See [version diff](../../Horizon_Changes_v2.diff), [protocol](../../Frozen_Protocol_v2.json), and [raw failure](../../runs/public_01/VALIDATION_FAILURE.json). Failure_Audit.json records unfinished IDs, final counters and raw hashes.
