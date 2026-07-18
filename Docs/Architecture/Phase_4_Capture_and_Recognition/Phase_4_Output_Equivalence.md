# Phase 4 Output Equivalence

## Capture

| Input | Previous output | Canonical output | Difference | Result |
| --- | --- | --- | --- | --- |
| New desktop session | Dated folder and established session keys | Same delegate result | None | Pass |
| Front/back JPEG bytes | `000001_front.jpg`, `000001_back.jpg` | Same delegate result | None | Pass |
| Completed pair | One row, `Complete`, `FRONT_BACK`, `latest=True` | Same values | None | Pass |
| Front-only mobile session | Front is complete without back | Same pairing rule | None | Pass |
| Current front only | `Waiting for Back` | Same status | None | Pass |
| Current front/back | `Ready for Next Card` | Same status | None | Pass |
| Invalid auto settings | Clamped values and `Medium` sensitivity | Same values | None | Pass |
| High sensitivity | Existing four thresholds | Same values | None | Pass |
| Queue next pending | Atomic claim and existing manifest shape | Same delegate result | None | Pass |
| Inventory conversion service | Same root, OBS manager, placeholder flag | Same dependencies | None | Pass |

## Recognition

There was no production CardVector recognition output before Phase 4.
CardUploader remains the external owner. Equivalence therefore applies to the
handoff:

| Contract | Previous behavior | Phase 4 behavior | Difference | Result |
| --- | --- | --- | --- | --- |
| Provider URL | Read configuration and open in browser | Adapter reads same configuration; UI opens browser | None | Pass |
| Capture context | Retained in active workflow job | Included in typed handoff and retained in job | Additive internal metadata only | Pass |
| Recognition execution | External CardUploader | External CardUploader | None | Pass |
| CSV return path | Existing Processing import | Unchanged | None | Pass |

No card name, set, number, candidate order, confidence, OCR evidence, diagnostic
path, or plain-text recognition result exists in the production CardVector
contract. Those comparisons are not applicable and are not claimed.

The same existing delegates execute all write, move, retry, and queue actions.
Temporary-directory tests confirm contract parity. No unexplained output
difference was observed.
