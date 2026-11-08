# Progress export format, version 1

This format is designed for one Microsoft Forms text answer
per student, with the answer retained as text in the downloaded workbook. The
form should also collect any identification or consent required by the
instructor. The encoded string itself includes the student's name.

## Envelope

The string is `0X1.` followed by unpadded RFC 4648 URL-safe Base64 (`A-Z`,
`a-z`, `0-9`, `-`, `_`). The decoded bytes are one zlib-wrapped DEFLATE stream
(RFC 1950), containing a UTF-8 encoded JSON object. There is no newline in the
export. `0X1.` identifies this application and format version; unknown versions
must be rejected, not interpreted as version 1.

JSON member ordering and whitespace are not significant. Producers should omit
unnecessary whitespace and encode Unicode directly as UTF-8 before compression.
Receivers may trim whitespace only at the two ends of the complete string; they
must not remove or alter characters within it. Restore Base64 padding before
decoding. Reject invalid Base64, invalid zlib data or checksum, trailing bytes,
invalid UTF-8, duplicate JSON object keys, invalid JSON, missing required fields,
or values that violate this specification. Impose reasonable input and
decompressed-size limits in the processor.

## JSON object

All fields below are required. Dates are Gregorian local calendar dates in
`YYYY-MM-DD`; they refer to the student's device's local time zone at the time
of recording, not necessarily the instructor's time zone.

| Key | Value |
| --- | --- |
| `n` | Array of two nonempty strings: firstname, lastname, as stored in the app. |
| `at` | Snapshot time in UTC, RFC 3339, e.g. `2026-11-08T20:00:00Z`. |
| `day` | Student's local date at snapshot time. |
| `s` | Object mapping question-type IDs to cumulative all-time correct-answer counts, not individual answers or questions. |
| `d` | Object mapping question-type IDs to cumulative correct-answer counts for `day` only. If the stored daily scores are from another day, export an empty object. |
| `since` | Local date on which usage tracking first started, or `null` if it has not started. Earlier usage is unknown, not zero. |
| `cut` | Boolean: true if older recorded usage dates were omitted from `t` due to the 100-date limit. |
| `t` | Object mapping at most 100 recorded local dates to active usage durations in **whole minutes**. |

Score counts and durations are nonnegative integers no greater than
9,007,199,254,740,991; booleans are not integers. A missing score ID means zero;
zero entries may be omitted. For each type, its `d` count must not exceed its
`s` count.

Select the 100 most recent **recorded usage dates**, ordered by calendar date,
not the last 100 calendar days. Include every selected date, even if its usage
rounds to zero minutes. Convert each accumulated local-storage duration from
milliseconds to minutes, rounding to the nearest whole minute with half a
minute rounded up: `(milliseconds + 30000) // 60000`. Do not round individual
sessions before summing. The limit applies only to exports; local storage keeps
the full history in milliseconds. If more than 100 dates exist, `cut` is true
and only the most recent 100 are exported; otherwise it is false.

Within the period covered by the export, a missing date means zero recorded
usage. If `cut` is true, the covered period starts at the earliest date in `t`;
earlier dates are unknown because they may have been omitted, not zero. If
`cut` is false, coverage starts at `since`, except that dates before `since`
explicitly present in `t` are also known. If `since` is null, `t` must be empty
and `cut` must be false. An empty `t` does not mean that no time was spent before
tracking was introduced. Tracking uses the device clock, so clock or time-zone
changes can affect dates and durations; `since` is the first recorded tracking
date, not proof of complete history. The data is an approximation, including
where usage rounds down to zero minutes.

The snapshot must include all known scores, including advanced scores even when
advanced mode is off. The exporter checkpoints the active timer before
capturing the snapshot. Preserve unrecognised stored question IDs instead of
silently dropping them. A processor must report such IDs as unmapped, retain
their counts and not invent a category for them. The category totals below are
the sum of all corresponding `s` counts; today's totals use `d` instead. The
dashboard average is the sum of the five category totals divided by five.

| Master category | Version 1 question-type IDs |
| --- | --- |
| `base_conversion` | `base_conversion`, `number_of_values`, `twos_comp_bin_to_den`, `twos_comp_den_to_bin`, `real_denary_to_bin`, `real_bin_to_den` |
| `binary_arithmetic` | `binary_addition`, `binary_shift`, `binary_subtraction`, `binary_multiplication` |
| `unit_conversion` | `unit_conversion`, `data_transfer` |
| `operators` | `operators_div_mod`, `operators_boolean` |
| `bit_patterns` | `ip_network_address`, `ip_host_id`, `ip_cidr_to_mask`, `ip_mask_to_cidr`, `ip_usable_hosts`, `ip_min_subnet`, `ip_broadcast_address`, `ip_first_last_host`, `image_representation`, `bitwise_operators` |

These IDs and their category assignments are frozen for version 1. New
incompatible semantics require a new version. Additional question IDs may be
preserved but must be treated as unmapped by version 1 processors.

## Test vector

One valid JSON payload is:

```json
{"n":["Ada","Lovelace"],"at":"2026-11-08T20:00:00Z","day":"2026-11-08","s":{"base_conversion":7,"binary_addition":3,"number_of_values":2},"d":{"base_conversion":1},"since":"2026-11-07","cut":false,"t":{"2026-11-07":2,"2026-11-08":1}}
```

One valid encoding of it is:

```text
0X1.eJxtjsEKgzAQRP9lzhFiCrXk1nuPPbWUsJoVAjYBYwQR_71rTxYKe5rZeTMrIuwTV09QuKWZB-oYLwWaYGG0OVd1XenL3Wir93vIn6flxxQpw65oKbPrUpx5zCEJuFFoQ6RxceR9mL7aSSGWd8ujS72baSgsWbMJ9S-iFieHKKMOjY00dkUW9jRkVpj26MG1Rh3nCWT7ALGEQo8
```

The all-time category totals are 9, 3, 0, 0, 0 in the table's order; the
average is 2.4. Compression settings can produce different valid strings for
the same payload.

## Size, privacy and trust

The example is 211 characters. Limiting the export to 100 recorded dates
prevents the usage-history portion growing indefinitely, but does not guarantee
every export fits: names and preserved unknown score IDs are not size-limited.
Microsoft Forms text answers have been [reported as
limited to 4,000 characters](https://learn.microsoft.com/en-us/answers/questions/5118644/microsoft-forms-word-limit); verify the actual limit in the intended form and
tenant before deployment. Excel cells have a separate 32,767-character limit.
The exporter uses a 4,000-character limit **before** copying and displays
over-limit text for transfer outside Forms without truncating it. This fixed
limit is not a guarantee of compatibility with every form.
The processor must report invalid or truncated cells with their workbook row.

Encoding is not encryption: anyone with the string can recover the name, scores
and usage history. Share it only with the intended instructor, and handle the
form and workbook accordingly. The zlib stream includes an Adler-32 checksum of
the uncompressed bytes; the decoder must validate it. It detects most accidental
copying errors but cannot guarantee detection of every corruption, and does not
protect against deliberate changes; students can modify local storage or forge exports.
These results are self-reported and must not be treated as tamper-proof.
