# Data snapshot: homelab-data-platform

These four CSV files are the output of the data generators in
<https://github.com/orbiane/homelab-data-platform> at commit
`5e8e25d7f79cb407402d7dd107a7694311bb9e9b` (`data_generation/generators/`), run once in this order with `PYTHONHASHSEED=0`:
`account_master`, `subscription`, `message_event`, `revenue_monthly`.

The generators aren't byte-reproducible: two of them write random `uuid4` event IDs. Every reviewer therefore uses **this one snapshot**, so that everyone queries identical data. `SHA256SUMS` lists the file hashes.

The generating code is MIT-licensed:

> MIT License
>
> Copyright (c) 2026 orbiane

The full licence text is copied next to this file as `LICENSE`. The files are copied here unchanged.
