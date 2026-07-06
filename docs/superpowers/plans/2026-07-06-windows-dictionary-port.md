# Windows Dictionary Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Windows version of the vocabulary app with local-first Chinese dictionary lookup.

**Architecture:** Keep Flask, CSV wordbook storage, and the browser UI. Replace macOS Dictionary lookup with a provider chain that checks local ECDICT SQLite/CSV resources, then falls back to the existing online English API, then manual entry.

**Tech Stack:** Python 3.10+, Flask, requests, pytest, SQLite, PowerShell, Windows batch.

---

### Restored Baseline

- [x] Flask app files restored.
- [x] Windows local dictionary service restored.
- [x] `resources/mini_ecdict.csv` restored.
- [x] `scripts/prepare_ecdict.py` restored.
- [x] `start-windows.ps1`, `start-windows.bat`, and `启动-Windows.bat` restored.
- [x] Tests restored and passing.
