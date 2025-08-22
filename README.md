# Tetris in python (pygame)

a simple tetris game made with python and pygame

## Requirements
- python 3.x
- pygame (´pip install -r requirements.txt´)
- pygame pinned to a tested version: see `requirements.txt` (recommended: `pip install -r requirements.txt`)

## Settings
You can toggle Ghost mode in the main menu. The project now also includes a small settings area (Debounce and Ghost style) which can be adjusted from the menu.

## Leaderboard format
Leaderboard entries are stored in `leaderboard.txt` in the format:

```
<score> <cols>x<rows> <name>
```

Example:
```
1234 10x20 Alice
```

Older entries (before this change) may appear as `<score> <name>` and will still be read.

## Menu shortcuts
- S or Enter: Start game
- G: toggle Ghost preview
- T: toggle Ghost style (filled/outline)
- D: cycle Debounce value (50/100/150/250 ms)
- 1-4: select grid preset (10x20, 10x40, 20x40, 40x40)


## How to run
1. clone the repository or download the ZIP
2. install dependencies:
  pip install -r requirements.txt 
3. run the game:
  python ".\tetris v1.py"
