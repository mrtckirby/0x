# Proposed progress export format, version 1

This is a specification for a future export feature and spreadsheet processor;
neither is implemented yet. It is designed for one Microsoft Forms text answer
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
| `s` | Object mapping question-type IDs to all-time correct-answer counts. |
| `d` | Object mapping question-type IDs to correct-answer counts for `day` only. If the stored daily scores are from another day, export an empty object. |
| `since` | Local date on which usage tracking first started, or `null` if it has not started. Earlier usage is unknown, not zero. |
| `t` | Object mapping local dates to active usage durations in **integer milliseconds**. |

Score counts and durations are nonnegative integers no greater than
9,007,199,254,740,991; booleans are not integers. A missing score ID means zero;
zero entries may be omitted. For each type, its `d` count must not exceed its
`s` count. Missing dates in `t` represent no recorded active time since
tracking began. An empty `t` does not mean that no time was spent before
tracking was introduced. If `since` is null, `t` must be empty. Tracking uses
the device clock, so clock or time-zone changes can affect these dates and
durations, including producing dates earlier than `since`; `since` is the
first recorded tracking date, not proof of complete history.

The snapshot must include all known scores, including advanced scores even when
advanced mode is off. A future exporter must checkpoint the active timer before
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
{"n":["Ada","Lovelace"],"at":"2026-11-08T20:00:00Z","day":"2026-11-08","s":{"base_conversion":7,"binary_addition":3,"number_of_values":2},"d":{"base_conversion":1},"since":"2026-11-07","t":{"2026-11-07":90000,"2026-11-08":60000}}
```

One valid encoding of it is:

```text
0X1.eJxtjsEKgzAQRP9lzhFiCtrm1nuPPVlK2JgUAjYBo4KI_95NTxa67OnN7OxsiNAPXB1B4JYWP1Dv8RSgCRpKqqaq60qe70pqWbZjn6P1R2SUoTdYyt70KS5-zCFxcCtgQ6RxNeRcmL7sJBDnt_WjSS-z0DB7vlU7p_6NqFnJIXKpw8eWP07FfiD6InnEsZZuCtr3D24tQBo
```

The all-time category totals are 9, 3, 0, 0, 0 in the table's order; the
average is 2.4. Compression settings can produce different valid strings for
the same payload.

## Size, privacy and trust

The example is 207 characters. Text is practical for typical progress, but daily
history grows indefinitely, so this format cannot guarantee every export will
fit in one Forms response. Microsoft Forms text answers have been [reported as
limited to 4,000 characters](https://learn.microsoft.com/en-us/answers/questions/5118644/microsoft-forms-word-limit); verify the actual limit in the intended form and
tenant before deployment. Excel cells have a separate 32,767-character limit.
A future exporter must check the configured form limit **before** copying,
report an over-limit error without truncating or discarding data, and provide an
alternative transfer method or an explicitly designed multi-field format.
The processor must report invalid or truncated cells with their workbook row.

Encoding is not encryption: anyone with the string can recover the name, scores
and usage history. Share it only with the intended instructor, and handle the
form and workbook accordingly. The zlib checksum detects accidental corruption,
not deliberate changes; students can modify local storage or forge exports.
These results are self-reported and must not be treated as tamper-proof.
