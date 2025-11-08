# Demo 01 - Basic crosswalk and validation

This demo shows CODEMAP working offline against its built-in terminology table
(no `--table` needed) and against the sample file in this folder.

## What it shows

1. **System detection** - CODEMAP infers the coding system from a code's shape:
   - `E11.9` -> ICD10
   - `4548-4` -> LOINC (with a valid mod-10 check digit)
   - `6809` -> RXNORM
   - `99213` -> CPT

2. **Validation** - Each code is checked for well-formedness and table membership.

3. **Crosswalk** - An ICD-10 diabetes code maps to the related lab test,
   medication, and procedure concepts.

## Commands

```sh
# Validate the sample codes (one per line)
python -m codemap validate --input demos/01-basic/sample_codes.txt --format json

# Crosswalk Type 2 diabetes (ICD-10 E11.9) to all mapped systems
python -m codemap crosswalk E11.9 --format json

# Only the medications (RxNorm) mapped from hypertension
python -m codemap crosswalk I10 --to RXNORM
```

## Expected result

- `validate` on the sample file reports each code's detected system and marks
  `E11.9`, `4548-4`, `6809`, and `99213` as `valid` and `known`. The bogus
  line `ZZZ999` is detected as `UNKNOWN` and counts as a finding, so the
  process exits with code **1** (useful as a CI gate).
- `crosswalk E11.9` returns at least three mapped concepts:
  - LOINC `4548-4` Hemoglobin A1c
  - RXNORM `6809` Metformin
  - (and reverse-linked concepts), exiting **0**.
- `crosswalk I10 --to RXNORM` returns RXNORM `29046` Lisinopril, exiting **0**.
