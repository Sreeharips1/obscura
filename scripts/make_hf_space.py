"""Packages the backend for a Hugging Face Docker Space.

    python scripts/make_hf_space.py

Creates build/hf_space/ . Copy its contents into your cloned Space repo.
"""
import os
import shutil

SRC = "backend"
OUT = os.path.join("build", "hf_space")

HEADER = """---
title: Obscura Backend
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
---

Obscura privacy gateway API.
"""

if os.path.isdir(OUT):
    shutil.rmtree(OUT)

os.makedirs(OUT)

shutil.copy(os.path.join(SRC, "Dockerfile"), OUT)
shutil.copy(os.path.join(SRC, "requirements.txt"), OUT)

shutil.copytree(
    os.path.join(SRC, "app"),
    os.path.join(OUT, "app"),
    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
)

with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write(HEADER)

print("Ready:", OUT)
print("Copy everything inside it into your Space repo, then commit and push.")
