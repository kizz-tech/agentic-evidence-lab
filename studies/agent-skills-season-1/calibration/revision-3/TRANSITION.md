# Calibration revision 3 to 4 transition

Revision 4 changes only Python formatting in the frontend external-resource
regular expression. The evaluator behavior, task fixture, treatment, runtime,
and candidate workspaces are unchanged. Evaluators are never mounted into agent
runs, so the retained revision 3 frontend candidates were re-evaluated under
the exact revision 4 evaluator without rerunning the model.

This is a byte-identity transition, not an invalidation or a new effect
observation. Revision 4 is the final public calibration contract represented by
the evidence receipts.
