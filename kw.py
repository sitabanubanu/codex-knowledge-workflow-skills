#!/usr/bin/env python
"""Compatibility entrypoint for the Knowledge Workflow CLI."""

from __future__ import annotations

from kw_cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
