# 0x - a path to mastery in the mathematical skills of Computer Science

Simple client-side Computer Science-oriented mathematics
practice built with Pyscript. 

It is designed to run in the browser and to be published as a static
site, available [here](https://0x.sunsquashed.uk/).

## What it does

- prompts for firstname and lastname when the app loads
- provides programmatically-generated questions on:
    - Base conversion
    - Binary arithmetic
    - Unit conversion
    - Number of values
    - Operators

- validates answers reactively with no submit button
- supplies a new question at the end of the list when a user answers a
  question correctly
- shows a sticky top dashboard with the student's name and scores
  for today and all time
- saves the students's name and scores to local storage

This app intentionally avoids server-side features, databases, APIs, and
filesystem persistence so it remains suitable for browser-only execution.
Personal data is stored and processed only on the client, minimising
data privacy risks.

0x was built by Tom Kirby, with a lot of help from Gemini and some help from Github Copilot.

0x is licensed under the GNU GPL version 3. For details see the LICENSING 
file.

## Smoke test

A minimal Playwright smoke test is included to verify app startup and question rendering.

```bash
npm install
npx playwright install --with-deps chromium
npm run test:smoke
```
