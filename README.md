# Formula Studio v1.0

**All-in-one offline STEM desktop suite** for students, educators, and technical authors — built with Python, PySide6, and Matplotlib. Full bilingual **English ⇄ Vietnamese** interface with instant theme switching (4 studio themes + 8 accent colors).

[![Version](https://img.shields.io/badge/version-v1.0-5B5BD6)](https://github.com/CornyIsmE0401/Formula-Studio/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-10B981)](LICENSE)

---

## Key Features

| Workspace | Highlights |
| :--- | :--- |
| **Math Formulas (LaTeX)** | Live WYSIWYG visual editor synced 2-way with LaTeX code, **385+ built-in formulas**, quick variable substitution & evaluation, 300 DPI PNG / SVG / native editable Microsoft Word Equation (`.docx`) export. |
| **Dynamic Geometry & Graphs** | GeoGebra-style canvas with **1%–1250% zoom**, 26 construction tools, **28 preset 2D/3D figures**, draggable labels & notes, live function plotting `y = f(x)` with coordinate trace, save/load `.geo`. |
| **Chemical Equations & Balancer** | Instant algebraic balancer (including redox & ionic equations), molar mass & elemental % calculator, **686+ verified chemical reactions** with reaction conditions. |
| **2D SMILES Structure Renderer** | Convert IUPAC names, condensed formulas, or SMILES strings into publication-ready 2D molecular structures with **307 categorized presets**. |
| **Molecule Sketcher** | ChemDraw-style 3-column 2D editor with single/double/triple/wedge/dash stereobonds, element hotkeys, hand pan (`H`), drag-box region erase (`E`), and 2D layout cleaning. |
| **Periodic Table & 705-Compound Wiki** | 118-element IUPAC Periodic Table with Bohr models, `↑↓` orbital diagrams, and audio pronunciation (`0.75×` / `1.0×` / `1.25×`); **705-compound Wikipedia-style Chemistry Wiki** with `★ Bookmarked` collections. |
| **Scientific Calculator** | Natural textbook display (fractions, roots, powers), `S⇔D` exact/decimal toggle, memory variables, and **43 step-by-step solvers** across algebra, calculus, matrices, statistics, geometry, and chemistry. |
| **Word Export & Formula OCR** | Batch export to native editable Microsoft Word Equations (`.docx`) or insert directly at cursor; scan math/chemical screenshots via Gemini AI OCR. |

---

## Download & Run (Windows)

### Option 1: Standalone `.exe` (No Python Required)
1. Go to [**Releases**](https://github.com/CornyIsmE0401/Formula-Studio/releases) and download `FormulaStudio.exe`.
2. Double-click to run — works completely offline.

### Option 2: Run from Source
```bash
git clone https://github.com/CornyIsmE0401/Formula-Studio.git
cd Formula-Studio
pip install -r requirements.txt
python main.py
```

Or on Windows, double-click `install.bat` (first time) and then `run.bat`.

---

## Build Windows Executable
Double-click `build_exe.bat` (requires Python 3.11–3.13 recommended for PyInstaller):
- `build_exe.bat` → single portable file `dist\FormulaStudio.exe`
- `build_exe.bat folder` → faster-startup folder build `dist\FormulaStudio\FormulaStudio.exe`

Run `python main.py --selftest` to verify core engines (Math render, Chemical balancer, Molecule renderer, Calculator, Natural display, Word `.docx` export).

---

## Author & License
Created by **ItzMe_Corniizt**. Released under the [MIT License](LICENSE).
