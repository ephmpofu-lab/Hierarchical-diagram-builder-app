import sys
sys.path.insert(0, r"C:\Users\abxmukk\diagram-builder")
from backend.tree import parse_outline_text

text = """ATS_02 Candidate Discovery (Level 1)
├── ATS_02 Orchestrator (Level 2)
├── FW_01 Scanner Configuration (Level 2)
│   ├── ScannerConfigurationEngine (Level 3)
│   └── MarketUniverseConfigurationEngine (Level 3)
└── FW_02 Market Scanner (Level 2)
    └── MarketUniverseEngine (Level 3)
"""

root = parse_outline_text(text)

def walk(node, depth=0):
    print("  " * depth + repr(node.label))
    for c in node.children:
        walk(c, depth + 1)

walk(root)
