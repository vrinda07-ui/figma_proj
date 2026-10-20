
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
INPUT = BASE / "dataset" / "labels" / "dashboard15_nodes_for_claude.json"
OUTPUT_DIR = BASE / "dataset" / "labels" / "claude_chunks"

CHUNK_SIZE = 250

nodes = json.loads(INPUT.read_text(encoding="utf-8"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for old_file in OUTPUT_DIR.glob("chunk_*.json"):
    old_file.unlink()

for start in range(0, len(nodes), CHUNK_SIZE):
    chunk = nodes[start:start + CHUNK_SIZE]
    chunk_number = start // CHUNK_SIZE + 1
    path = OUTPUT_DIR / f"chunk_{chunk_number:02d}.json"
    path.write_text(
        json.dumps(chunk, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"{path.name}: {len(chunk)} nodes")

print(f"\nTotal nodes: {len(nodes)}")
print(f"Total chunks: {(len(nodes) + CHUNK_SIZE - 1) // CHUNK_SIZE}")
print(f"Output folder: {OUTPUT_DIR}")
