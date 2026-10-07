# SpoolLens in 14 seconds

The main README uses four scenes from real keyboard interaction with SpoolLens:

1. Select the fields once (3.6 s): ITEM, QTY, PRICE, and inherited WAREHOUSE
2. Replay the rule on recurring reports (2.8 s): a second report, the same saved rule, new candidate rows
3. Bad input never silently becomes a clean CSV (3.6 s): a malformed quantity, an unresolved line, and an actual blocked clean-export attempt
4. Every value is traceable to its source (4.0 s): inspect a valid quantity, highlight its original characters including padding, and show the actual clean CSV

The reports are small synthetic inventory examples. They are separate inputs: the malformed report is never repaired or exported as a clean CSV. The last scene returns to the valid report.

Terminal crops preserve the captured characters and highlights. Captions, arrows, color, and layout are editorial annotations. The hero combines four separate field-selection captures; the replay pane removes empty inter-column padding. The final scene combines the source inspection and the CSV subsequently exported from that same valid report. Setup and navigation are omitted from the short sequence.

The [original 25-second technical walkthrough](../spoollens-demo.gif), [captions, and full terminal captures](../README.md) remain available unchanged.
