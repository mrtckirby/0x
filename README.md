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
- displays today's active usage time and stores daily durations locally; time
  counts while the page is visible, up to one minute after the last pointer,
  keyboard, input or scroll interaction. Tracking starts on interaction after
  starting or returning to the page, and resumes on interaction after hiding it
- clears usage history as well as scores when starting over
- includes previously saved number-of-values scores in base conversion totals;
  the average is calculated across the five master categories

Usage history starts when this feature first records an interaction; earlier
usage cannot be recovered. Durations are split at the device's local midnight
and saved periodically and when the page is hidden or closed. Browser shutdowns,
clock changes and suspended tabs can make the figures approximate. Use one
app tab at a time: separate tabs share storage but do not coordinate their
in-memory scores or timers and can overwrite one another.

The proposed compact, shareable progress format is documented in
[`EXPORT_FORMAT.md`](EXPORT_FORMAT.md). Exporting and spreadsheet processing
are not implemented yet.

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
