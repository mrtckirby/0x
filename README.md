# 0x - a path to mastery in the mathematical skills of Computer Science

Simple client-side Computer Science-oriented mathematics
practice built with Pyscript. 

It is designed to run in the browser and to be published as a static
site, available [here](https://0x.sunsquashed.uk/).

## What it does

- prompts for firstname and lastname when the app loads
- provides programmatically-generated questions on:
    - Base conversion, including number of values and highest representable value
    - Binary arithmetic
    - Unit conversion
    - Operators
    - Bit patterns: IPv4 addressing (advanced), representing images, and 4-bit bitwise operators

- gently favours topics with lower all-time correct counts when choosing new questions
- lets students focus on one master category, replacing the current questions;
  the focus is saved across reloads and can be cleared with the × button
- scorecards also allow focusing on a single question type; turning off
  advanced questions while focused on an advanced type returns to its master category
- respects the advanced questions setting when choosing focused questions
- validates answers reactively with no submit button
- supplies a new question at the end of the list when a user answers a
  question correctly
- shows a sticky top dashboard with the student's name and scores
  for today and all time
- opens a scorecard from each dashboard score, showing today and all-time
  counts by question type; the average scorecard includes all categories
- shows advanced question types after standard types in scorecards only when
  advanced questions are enabled; category totals still include all scores
- saves the students's name and scores to local storage
- opens a progress menu by clicking the student's name, with name editing,
  score export, backup save/load and a clear-progress action
- displays today's active usage time and stores daily durations locally; time
  counts while the page is visible, up to one minute after the last pointer,
  keyboard, input or scroll interaction. Tracking starts on interaction after
  starting or returning to the page, and resumes on interaction after hiding it
- awards badges named after computing pioneers for correct answers and for
  active practice on different days. Earned engagement badges appear to the
  left of the questions and achievement badges to the right on wide screens;
  open **Badges** in the progress menu to see the full collection on any screen
- clears usage history as well as scores when starting over
- includes previously saved number-of-values scores in base conversion totals;
  the average is calculated across the five master categories

Usage history starts when this feature first records an interaction; earlier
usage cannot be recovered. Durations are split at the device's local midnight
and saved periodically and when the page is hidden or closed. Browser shutdowns,
clock changes and suspended tabs can make the figures approximate. Use one
app tab at a time: separate tabs share storage but do not coordinate their
in-memory scores or timers and can overwrite one another.

## Badges

Badge progress is calculated from locally stored all-time scores and usage.
The engagement badges require both active time and correct answers: Ada Lovelace
requires 10 minutes total and 2 answers; Grace Hopper, Margaret Hamilton and
Donald Knuth require at least 5 minutes on 3, 10 and 30 different local days,
plus 5, 15 and 50 answers respectively. Days do not need to be consecutive.
Correct answers are counted all-time, not necessarily on each practice day.

Achievement badges reward 10 and 100 answers overall, 25 in Base conversion,
25 in Operators, 25 across Binary arithmetic and Bit patterns, and 10 in each
of the five categories. The collection shows the requirements and progress for
locked badges. Select an earned badge to read about its namesake and criterion.
New awards are announced and briefly animated, respecting reduced-motion
preferences. Existing and restored awards appear without celebrations. Backups
preserve the underlying data; clearing progress removes the awards. Earlier
usage that was not recorded cannot count towards engagement badges.

## Sharing and processing scores

Students can click their name or profile icon, select **Copy progress to clipboard...** and paste the copied text into the
instructor's Microsoft Forms long-answer question. If clipboard access fails,
the page displays the full text for manual copying. If it exceeds 4,000
characters, the page displays the full text instead and warns not to paste it
into Forms; use an alternative transfer method. Check the actual answer limit
for the form before use. The export includes the name entered in 0x, cumulative
question-type scores and up to 100 recorded usage days. It is not encrypted or
tamper-proof. See [`EXPORT_FORMAT.md`](EXPORT_FORMAT.md).

The same name menu can save progress to a `firstname-surname.0xf` file or load a previously
saved backup. The `.0xf` file contains JSON in the same format as earlier `.json`
backups, which can still be loaded. Backups contain the same fields as the browser's
`cs_maths_state` local storage entry, including the name, settings, complete
scores and all recorded usage days (not the compact instructor export). Loading
validates the file (maximum 20 MB) and immediately replaces the current data;
daily scores from a previous day are reset as on a normal reload. A backup can
also be loaded from the start screen. If browser storage is blocked, the app
warns that progress exists only for the current session; save backups regularly
and load one at the next visit. Backups are not encrypted: store them securely.

For spreadsheet processing, configure the form to record respondents' names
and email addresses and download its `.xlsx` responses. Install Python and run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python process_forms.py responses.xlsx scores.xlsx
```

By default the active worksheet and the unique column containing `0X1.`
exports are used. Use `--sheet "Sheet name"` to select another worksheet, or
`--export-column "Exact question header"` if detection is ambiguous or no
prefix is present. `--include-daily` adds snapshot-day category and question
type columns; all-time scores are always included. Each selected response has
Forms name, email and completion time, the 0x name and snapshot metadata, all
category totals and question-type counts, and a column per local calendar day
of usage. Unmapped question types have separate columns and are reported.

Emails are matched case-insensitively; the latest valid submission by Forms
completion time is used for each email, with the later workbook row breaking
ties. Invalid later submissions are reported to stderr and an earlier valid
submission is tried. Rows without a name, email or usable completion time and
students with no usable submission are reported and skipped. If no submissions
are usable, no output is written. Dates without recorded usage are zero only
within that student's covered history; blank cells mean unknown or outside the
snapshot. The usage truncation column identifies exports that omit older
recorded days. Output overwrites an existing output file; input and output must
be different files.

This app intentionally avoids server-side features, databases, APIs, and
filesystem persistence so it remains suitable for browser-only execution.
Personal data is stored and processed only on the client, minimising
data privacy risks.

0x was built by Tom Kirby, with a lot of help from Gemini and some help from Github Copilot.

0x is licensed under the GNU GPL version 3. For details see the LICENSING 
file.

## Styling

Category colours are defined once, in `input.css` (as `@theme` tokens bound
via `data-cat` attributes). `style.css` is generated and not committed: run
`npm ci && npm run build:css` to build it (CI does this on deploy).

## Smoke test

A minimal Playwright smoke test is included to verify app startup and question rendering.

```bash
npm install
npx playwright install --with-deps chromium
npm run test:smoke
```
