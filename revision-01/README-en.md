# Information, Interaction, and Decision in Dynamical Systems

**Kevin T.N. — Epistemologist**

Full English edition, 28 November 2026. Open **paper-en.pdf** to read the monograph. Its linked contents give access to the 23 numbered sections, four appendices and references.

## First edition

This first edition sets out the questions, assumptions, and results that define the project at this stage. Future work may follow a question of particular interest, as time permits, or grow out of a specific practical need. As the work develops, later editions will incorporate corrections and extensions. Any change to a result will include a fresh review of its proof and a rerun of the relevant computational checks.

## Reading the two main results together

Sections 7–12 count the positional interval decisions that can survive perturbation. Sections 13–16 determine what a causal remeasurement protocol can reveal when the source changes during communication. Section 17 connects them at the decision time. Its six-interval example shows how coordinate errors and uncertainty in a shared offset combine in the exact decision criterion. Sections 18–21 deal with interconnection, deadlines, arithmetic implementation and application designs.

## Editable manuscript

The entry point is `paper-en.tex`. The text and proofs are in `english/`. The bibliography is in `references.tex`. For the supplied layout, install XeLaTeX and the Times New Roman, Arial and Consolas fonts. Run the following command in the directory containing this file until the references and contents are stable.

```sh
xelatex -interaction=nonstopmode -halt-on-error paper-en.tex
```

## Mathematical supplement

From `supplement/`, run the finite checks with a new output directory.

```sh
python verify.py --out verification-new
```

To include the 17 checked Lean declarations, supply a Lean executable. The recorded run used Lean 4.34.0-rc1 and Python 3.12.10.

```sh
python verify.py --lean /path/to/lean --out verification-lean-new
```

The original receipts are in `supplement/verification-01/`. Appendix D describes the exact scope of the written proofs, formal proofs and finite computations. The supplement contains the public mathematical examples and requires no external dataset.
