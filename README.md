# cs-maths-practice

Simple client-side CS maths practice prototype built with Pyscript.
It is designed to run in the browser and to be published as a static
site.

## What it does

- prompts for firstname and lastname when the app loads
- keeps session state in memory only while the browser tab remains open
- shows a sticky top dashboard with the student's name and scores for question
  types `a`, `b`, `c`, and `d`
- renders an endless scrolling list of placeholder questions
- validates answers reactively with no submit button
- turns an answer field green when the placeholder answer is correct

For the placeholder questions, the correct answer is simply the question number.
For example, question `12` is correct when the answer box contains `12`.

This app intentionally avoids server-side features, databases, APIs, and
filesystem persistence so it remains suitable for browser-only execution.
