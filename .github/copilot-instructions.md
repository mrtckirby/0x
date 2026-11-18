# Project guide

- 0x is a static, browser-only computer science maths practice app. The UI,
  application logic and inline Python run through PyScript in `index.html`.
- Edit `input.css` for styling; `style.css` is generated and must not be
  committed. Build it with `npm run build:css`.
- `process_forms.py` processes exported scores into spreadsheets. Keep changes
  to the export format consistent with `EXPORT_FORMAT.md`, the browser app
  and the processor. See `README.md` for app and processing details.

# Development and tests

- Install JavaScript dependencies with `npm ci`; install Python dependencies
  with `python -m pip install -r requirements.txt`.
- Install the browser with `npx playwright install --with-deps chromium`.
  `npm run test:smoke` runs the Playwright suite; to run a focused test use
  `npx playwright test tests/<name>.spec.js`. Playwright builds CSS and starts
  a local server using `playwright.config.js`.
- Run processor tests with `python -m unittest discover -s tests -p 'test_*.py'`.
  The standalone `tests/*_checks.py` scripts test extracted app logic with
  Python and can be run individually, for example `python tests/export_checks.py`.
- Browser tests load PyScript from `pyscript.net` and may also fetch its Python
  interpreter. If startup fails, check blocked requests and DNS; a local server
  or a successful CSS build alone does not mean the Python app has started.
