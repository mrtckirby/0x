# cs-maths-practice

Simple client-side CS maths practice prototype built with [Flet](https://flet.dev/).
It is designed to run in the browser via Pyodide and to be published as a static
site with `flet publish`.

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

## Local development

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app in a browser:

   ```bash
   flet run --web main.py
   ```

## Publish as a static site

Build the Pyodide-powered static site with:

```bash
flet publish main.py
```

This app intentionally avoids server-side features, databases, APIs, and
filesystem persistence so it remains suitable for browser-only execution.