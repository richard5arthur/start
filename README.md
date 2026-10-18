# start

A starting point for a new Python project.

## Status

This repository is in its initial stage. It currently contains:

| File         | Purpose                                                                                   |
| ------------ | ----------------------------------------------------------------------------------------- |
| `README.md`  | This file — an overview of the project.                                                    |
| `.gitignore` | The standard Python ignore rules (bytecode, virtual environments, build output, caches, etc.). |

No application code has been added yet.

## Getting started

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/richard5arthur/start.git
cd start
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

As the project grows, install its dependencies with:

```bash
pip install -r requirements.txt
```

(once a `requirements.txt` or `pyproject.toml` has been added).

## Suggested layout

As code is added, a conventional structure keeps things easy to navigate:

```
start/
├── src/            # application / library code
├── tests/          # tests (e.g. pytest)
├── requirements.txt or pyproject.toml
└── README.md
```

## Contributing

1. Create a branch for your change.
2. Commit with clear, descriptive messages.
3. Open a pull request against `master`.

## License

No license has been chosen yet. Until one is added, all rights are reserved by the repository owner.
