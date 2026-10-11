import json
from pathlib import Path

import generate_candidates as gc


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "dataset" / "new_dashboard" / "figma_data.json"

OUTPUT_DIR = ROOT / "dataset" / "new_candidates"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "new_dashboard_candidates.json"


# ============================================================
# FLATTEN FIGMA DOCUMENT
# ============================================================

def flatten_nodes(node, parent_id=None):
    """
    Convert Figma's nested document structure into
    the flat node structure expected by our preprocessing code.
    """

    nodes = []
    current = dict(node)

    # Add parent information
    current["parent_id"] = parent_id

    # Figma REST API stores TEXT content in "characters".
    # Our existing preprocessing expects "text".
    if current.get("type") == "TEXT":
        current["text"] = current.get("characters", "")

    # Figma REST API often stores geometry inside
    # absoluteBoundingBox rather than directly as x/y/width/height.
    bbox = current.get("absoluteBoundingBox")

    if bbox:
        current["x"] = bbox.get("x", 0)
        current["y"] = bbox.get("y", 0)
        current["width"] = bbox.get("width", 0)
        current["height"] = bbox.get("height", 0)

    nodes.append(current)

    # Recursively flatten children
    for child in current.get("children", []):
        nodes.extend(
            flatten_nodes(
                child,
                parent_id=current.get("id")
            )
        )

    return nodes


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("PROCESSING NEW FIGMA DASHBOARD")
    print("=" * 60)

    print("Reading:", INPUT_FILE)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # The new Figma export has:
    #
    # document
    #   └── children
    #
    document = data.get("document")

    if not document:
        print("ERROR: 'document' not found in Figma JSON.")
        return

    # Flatten entire Figma tree
    nodes = []

    for child in document.get("children", []):
        nodes.extend(
            flatten_nodes(
                child,
                parent_id=document.get("id")
            )
        )

    print("Total Figma nodes:", len(nodes))

    if len(nodes) == 0:
        print("ERROR: No nodes found after flattening.")
        return

    # Build maps using the SAME logic as training pipeline
    node_map, children = gc.make_maps(nodes)

    candidates = []

    # ========================================================
    # GENERATE CANDIDATES
    # ========================================================

    for node in nodes:

        if not gc.is_container(node):
            continue

        node_id = node.get("id")

        info = gc.stats(
            node_id,
            node_map,
            children
        )

        if gc.is_component_candidate(node, info):

            candidate = gc.build_candidate(
                node,
                info,
                "new_dashboard"
            )

            candidates.append(candidate)

    # ========================================================
    # REMOVE NESTED CANDIDATES
    # ========================================================

    candidates = gc.remove_nested(
        candidates,
        node_map,
        children
    )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    candidates = list(
        {
            c["candidate_id"]: c
            for c in candidates
        }.values()
    )

    # ========================================================
    # SORT
    # ========================================================

    candidates.sort(
        key=lambda c: (
            float(c.get("y") or 0),
            float(c.get("x") or 0)
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    output = {
        "dashboard": "new_dashboard",
        "candidate_count": len(candidates),
        "candidates": candidates
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print()
    print("=" * 60)
    print("NEW DASHBOARD CANDIDATES GENERATED")
    print("=" * 60)

    print("Candidates:", len(candidates))
    print("Output:", OUTPUT_FILE)

    print()

    for i, candidate in enumerate(candidates, 1):

        print(
            f"{i}. "
            f"{candidate.get('candidate_id')} | "
            f"{candidate.get('name')} | "
            f"score={candidate.get('candidate_score')}"
        )


if __name__ == "__main__":
    main()