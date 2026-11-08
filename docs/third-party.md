# PNC starter provenance

Source: https://github.com/devfulcrum/pnc-utd-hackathon-2026

Pinned revision: `55999aba3561270778f7830026bae666c5428740`.

Upstream license: Apache License 2.0, retained in `vendor/pnc-utd-hackathon-2026/LICENSE` and copied to `docs/pnc-LICENSE.txt` for the derived demo data. The full upstream checkout is kept local and ignored by this repository. `scripts/bootstrap-pnc.ps1` obtains the pinned revision on a fresh checkout.

This package reads the upstream synthetic CSV data, and its demo output and evaluation reports derive from that data. Toolkit financial calculations were reviewed as the foundation for the new intelligence layer. No upstream source files are modified. FinPilot's functions implement the blueprint's daily ML, weighted scoring and Guardian workflow separately from the starter's signed-JSON monthly examples.

Keep the upstream license with any redistributed upstream source or dataset. The bootstrap retains the upstream license automatically. Do not commit the nested vendor checkout as an accidental Git submodule.
