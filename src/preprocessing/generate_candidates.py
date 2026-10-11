
import json
import os
import re
from collections import defaultdict

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

DASHBOARD_DIR = os.path.join(BASE_DIR, "dataset", "dashboards")
OUTPUT_DIR = os.path.join(BASE_DIR, "dataset", "candidates")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# CONTAINER TYPES
# ============================================================

CONTAINER_TYPES = {
    "FRAME", "COMPONENT", "COMPONENT_SET",
    "INSTANCE", "GROUP", "SECTION"
}

ROOT_NAMES = {
    "dashboard", "healthcare dashboard", "health dashboard",
    "medical dashboard", "medical dashboard design",
    "01 dashboard landing page", "01 dashboard - landing page",
    "13 configurations", "additional dashboard components light theme",
    "data visualization", "cover", "design", "page 1",
    "desktop - 1"
}

INTERNAL_NAMES = {
    "chart", "bars", "bar", "points", "map", "legend",
    "plot area", "grid lines", "grid line", "x axis", "y axis",
    "axis", "axes", "table header", "table header title",
    "table body", "table footer", "pagination", "table pagination",
    "dept list", "department list", "demographics body",
    "demographics legend", "nav list", "navigation list",
    "sidebar footer", "sidebar header", "top menu", "side menu",
    "toolbar", "breadcrumb", "breadcrumbs", "header", "footer",
    "icon & text"
}

INTERNAL_WORDS = (
    "grid line", "plot area", "mask group",
    "table header", "table body", "table footer"
)

UI_WORDS = (
    "sidebar", "side nav", "navigation", "navbar", "topbar",
    "logo", "notification icon", "search bar", "settings",
    "log out", "logout", "support", "technical help",
    "download report", "language", "application settings",
    "contact management", "chat with visitors", "top menu",
    "side menu", "toolbar", "breadcrumbs", "breadcrumb",
    "advanced search", "search", "button", "menu item"
)

SEMANTIC_WORDS = (
    "kpi", "metric", "patient", "patients", "doctor", "doctors",
    "appointment", "appointments", "admission", "admissions",
    "revenue", "payment", "payments", "inventory", "pharmacy",
    "medicine", "medicines", "diagnostic", "diagnostics",
    "health index", "overview", "statistics", "analytics",
    "performance", "demographics", "gender", "survey", "report",
    "reports", "activity", "activities", "schedule", "calendar",
    "table", "chart", "graph", "surgery", "surgeries", "covid",
    "disease", "symptom", "treatment", "operations",
    "bed occupancy", "hospital", "onboarding", "listening",
    "music", "status", "total", "trend", "percentage",
    "distribution", "comparison", "monthly", "weekly"
)

NUMBER_RE = re.compile(
    r"^[\$₹€£]?\s*[\d,.]+\s*%?\s*[KkMmBb]?$"
)

DATE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b"
    r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    re.IGNORECASE
)


# ============================================================
# NORMALIZATION AND TEXT EXTRACTION
# ============================================================

def norm(value):
    value = str(value or "").lower().strip()
    value = re.sub(r"[_-]+", " ", value)
    return re.sub(r"\s+", " ", value)


def extract_node_text(node):
    """
    Supports flattened text fields and native Figma TEXT nodes.
    Figma API text is usually stored in 'characters'.
    """
    value = node.get("text")

    if isinstance(value, str) and value.strip():
        return value.strip()

    characters = node.get("characters")

    if isinstance(characters, str) and characters.strip():
        return characters.strip()

    return ""


def flatten_nodes(node, parent_id=None):
    """Convert a nested Figma tree to a flat list with parent IDs."""
    result = []

    if not isinstance(node, dict):
        return result

    current = dict(node)

    if parent_id is not None:
        current["parent_id"] = parent_id

    # Normalize native Figma text into the field used downstream.
    if current.get("type") == "TEXT":
        current["text"] = extract_node_text(current)

    result.append(current)

    current_id = current.get("id")

    for child in current.get("children", []) or []:
        result.extend(flatten_nodes(child, current_id))

    return result


def load_nodes(data):
    """Load either flattened JSON or a native Figma API export."""

    if isinstance(data.get("nodes"), list):
        print("Detected format: nodes")
        nodes = data["nodes"]

        # Normalize flattened nodes too.
        for node in nodes:
            if node.get("type") == "TEXT":
                node["text"] = extract_node_text(node)

        return nodes

    document = data.get("document")

    if isinstance(document, dict):
        print("Detected format: document -> children")

        nodes = []
        for child in document.get("children", []) or []:
            nodes.extend(flatten_nodes(child))

        return nodes

    # Also accept a directly exported tree.
    if isinstance(data.get("children"), list):
        print("Detected format: children")

        return flatten_nodes(data)

    print("WARNING: Unrecognized JSON structure.")
    return []


# ============================================================
# DIMENSIONS AND POSITION
# ============================================================

def get_dimensions(node):
    bbox = node.get("absoluteBoundingBox") or {}

    try:
        width = float(
            node.get("width")
            if node.get("width") is not None
            else bbox.get("width", 0)
        )
    except (TypeError, ValueError):
        width = 0

    try:
        height = float(
            node.get("height")
            if node.get("height") is not None
            else bbox.get("height", 0)
        )
    except (TypeError, ValueError):
        height = 0

    # Some exports use size fields instead of top-level dimensions.
    size = node.get("size") or {}

    if width <= 0:
        try:
            width = float(size.get("x", 0))
        except (TypeError, ValueError):
            pass

    if height <= 0:
        try:
            height = float(size.get("y", 0))
        except (TypeError, ValueError):
            pass

    return max(0, width), max(0, height)


def get_position(node):
    bbox = node.get("absoluteBoundingBox") or {}

    def read(key):
        value = node.get(key)

        if value is None:
            value = bbox.get(key, 0)

        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    return read("x"), read("y")


# ============================================================
# NODE MAPS AND TREE HELPERS
# ============================================================

def is_container(node):
    return node.get("type") in CONTAINER_TYPES


def make_maps(nodes):
    node_map = {
        node["id"]: node
        for node in nodes
        if node.get("id") is not None
    }

    children = defaultdict(list)

    for node in nodes:
        parent = node.get("parent_id")
        node_id = node.get("id")

        if parent in node_map and node_id is not None:
            children[parent].append(node_id)

    return node_map, children


def descendants(node_id, children):
    result = []
    stack = list(children.get(node_id, []))
    seen = set()

    while stack:
        child_id = stack.pop()

        if child_id in seen:
            continue

        seen.add(child_id)
        result.append(child_id)
        stack.extend(children.get(child_id, []))

    return result


def ancestor_ids(node_id, node_map):
    result = []
    current = node_map.get(node_id, {})
    seen = set()

    parent = current.get("parent_id")

    while parent and parent not in seen:
        seen.add(parent)
        result.append(parent)
        current = node_map.get(parent, {})
        parent = current.get("parent_id")

    return result


# ============================================================
# TEXT AND GRAPHICAL STATISTICS
# ============================================================

def stats(node_id, node_map, children):
    node = node_map[node_id]

    descendant_nodes = [
        node_map[item_id]
        for item_id in descendants(node_id, children)
        if item_id in node_map
    ]

    texts = [
        extract_node_text(item)
        for item in descendant_nodes
        if item.get("type") == "TEXT"
        and extract_node_text(item)
    ]

    direct_nodes = [
        node_map[item_id]
        for item_id in children.get(node_id, [])
        if item_id in node_map
    ]

    numeric = [
        text for text in texts
        if NUMBER_RE.match(text) or re.search(r"\d", text)
    ]

    vectors = sum(n.get("type") == "VECTOR" for n in descendant_nodes)
    lines = sum(n.get("type") == "LINE" for n in descendant_nodes)
    ellipses = sum(n.get("type") == "ELLIPSE" for n in descendant_nodes)
    rectangles = sum(n.get("type") == "RECTANGLE" for n in descendant_nodes)

    width, height = get_dimensions(node)

    return {
        "texts": texts,
        "text_count": len(texts),
        "numeric_count": len(numeric),
        "date_count": sum(bool(DATE_RE.search(t)) for t in texts),
        "vector_count": vectors,
        "line_count": lines,
        "ellipse_count": ellipses,
        "rectangle_count": rectangles,
        "graphic_count": vectors + lines + ellipses + rectangles,
        "direct_count": len(direct_nodes),
        "direct_container_count": sum(is_container(n) for n in direct_nodes),
        "descendant_count": len(descendant_nodes),
        "width": width,
        "height": height,
        "area": width * height,
        "aspect_ratio": width / height if height > 0 else 0
    }


# ============================================================
# CLASSIFICATION SIGNALS
# ============================================================

def is_internal(node):
    name = norm(node.get("name"))

    return (
        name in INTERNAL_NAMES
        or name.startswith("row ")
        or any(word in name for word in INTERNAL_WORDS)
    )


def is_ui(node):
    name = norm(node.get("name"))

    return (
        name in UI_WORDS
        or any(name.startswith(word + " ") for word in UI_WORDS)
        or "sidebar" in name
        or "side nav" in name
        or "top menu" in name
        or "side menu" in name
    )


def semantic_strength(node, info):
    haystack = (
        norm(node.get("name")) + " " +
        " ".join(info["texts"]).lower()
    )

    return sum(word in haystack for word in SEMANTIC_WORDS)


def strong_component_signal(node, info):
    haystack = (
        norm(node.get("name")) + " " +
        " ".join(info["texts"]).lower()
    )

    strong_phrases = (
        "diagnostics", "health index", "patient overview",
        "patient data", "hospital survey", "medical treatment",
        "heart surgeries", "patient statistics", "recent payments",
        "payments list", "inventory status", "new patients",
        "total doctors", "total patients", "appointment",
        "appointments", "revenue", "listening", "music", "status",
        "bed occupancy", "gender distribution", "monthly report"
    )

    return sum(phrase in haystack for phrase in strong_phrases)


def looks_like_layout_wrapper(node, info):
    name = norm(node.get("name"))

    if name in ROOT_NAMES:
        return True

    wrapper_names = {
        "main content", "content area", "dashboard content",
        "kpis row", "split row", "main row", "content row",
        "dashboard row", "top row", "bottom row",
        "paragraph container"
    }

    if name in wrapper_names:
        return True

    if name.startswith("13 configurations"):
        return True

    # Exclude likely whole-page wrappers, not all large containers.
    if info["width"] >= 1200 and info["height"] >= 650:
        return True

    if (
        info["direct_container_count"] >= 5
        and info["area"] >= 100000
        and info["text_count"] < 3
    ):
        return True

    return False


def is_small_ui_container(node, info):
    if info["area"] > 30000:
        return False

    if is_ui(node):
        return True

    name = norm(node.get("name"))

    if name in {"icon", "avatar", "profile image", "logo"}:
        return True

    if (
        info["width"] <= 300
        and info["height"] <= 90
        and info["text_count"] <= 3
    ):
        # Keep a semantically named metric/card if it has a value.
        if semantic_strength(node, info) > 0 and info["numeric_count"] > 0:
            return False

        return True

    all_text = " ".join(info["texts"]).lower()

    if "go to " in all_text:
        return True

    return False


def score(node, info):
    name = norm(node.get("name"))

    value = min(4, semantic_strength(node, info))

    if info["text_count"] >= 2:
        value += 2

    if info["numeric_count"] >= 1:
        value += 1

    if info["numeric_count"] >= 3:
        value += 1

    if info["graphic_count"] >= 3:
        value += 1

    if info["graphic_count"] >= 8:
        value += 1

    if info["ellipse_count"] >= 2:
        value += 1

    if info["line_count"] >= 4:
        value += 1

    if info["direct_container_count"] >= 2:
        value += 1

    if info["area"] >= 20000:
        value += 1

    if info["area"] >= 50000:
        value += 1

    if name.startswith("element "):
        value += 1

    return value


# ============================================================
# CANDIDATE DECISION
# ============================================================


def is_component_candidate(node, info):
    name = norm(node.get("name"))

    if is_internal(node):
        print(f"REJECT internal: {name!r}")
        return False

    if is_ui(node):
        print(f"REJECT UI: {name!r}")
        return False

    if info["width"] < 70 or info["height"] < 40:
        print(
            f"REJECT dimensions: {name!r} "
            f"{info['width']}x{info['height']}"
        )
        return False

    if looks_like_layout_wrapper(node, info):
        print(f"REJECT wrapper: {name!r}")
        return False

    if is_small_ui_container(node, info):
        print(f"REJECT small UI container: {name!r}")
        return False


    sem = semantic_strength(node, info)
    strong = strong_component_signal(node, info)
    candidate_score = score(node, info)

    # Explicitly named KPI cards.
    if name.startswith(("kpi", "metric")) and info["area"] >= 4000:
        return True

    # Explicit component names from API exports.
    if (
        name.startswith("component ")
        and info["area"] >= 5000
        and (info["text_count"] >= 1 or info["graphic_count"] >= 2)
    ):
        return True

    # Named elements from older exports.
    if name.startswith("element ") and info["area"] >= 15000:
        return info["text_count"] > 0 or info["graphic_count"] >= 3

    # Strongly meaningful content.
    if (
        strong >= 1
        and info["area"] >= 8000
        and (info["text_count"] >= 1 or info["graphic_count"] >= 3)
    ):
        return True

    # KPI cards and data tables.
    if (
        info["area"] >= 8000
        and info["text_count"] >= 2
        and info["numeric_count"] >= 1
        and (
            info["direct_container_count"] >= 1
            or info["graphic_count"] >= 2
        )
    ):
        return True

    # Charts, plots, and graphical groups.
    if (
        info["area"] >= 10000
        and (
            info["graphic_count"] >= 5
            or info["line_count"] >= 4
            or info["ellipse_count"] >= 3
        )
        and (info["text_count"] >= 1 or sem >= 1)
    ):
        return True

    # Semantic components.
    if (
        info["area"] >= 15000
        and sem >= 1
        and info["text_count"] >= 2
    ):
        return True

    # Generic group/frame: use structure and content, not its name alone.
    if (
        info["area"] >= 20000
        and info["text_count"] >= 3
        and (
            info["graphic_count"] >= 2
            or info["direct_container_count"] >= 1
        )
        and candidate_score >= 4
    ):
        return True

    # Unnamed/generic visual container: allow a strong graphical signal
    # even when the API export has no readable text.
    if (
        info["area"] >= 25000
        and info["graphic_count"] >= 8
        and info["descendant_count"] >= 10
    ):
        return True

    print(
        f"REJECT no rule matched: {name!r} "
        f"type={node.get('type')} "
        f"size={info['width']}x{info['height']} "
        f"texts={info['text_count']} "
        f"graphics={info['graphic_count']} "
        f"score={candidate_score}"
    )
    return False


# ============================================================
# BUILD CANDIDATE
# ============================================================

def build_candidate(node, info, dashboard):
    name = norm(node.get("name"))
    texts = info["texts"]
    x, y = get_position(node)

    return {
        "candidate_id": node.get("id"),
        "name": node.get("name"),
        "type": node.get("type"),
        "parent_id": node.get("parent_id"),
        "x": x,
        "y": y,
        "width": info["width"],
        "height": info["height"],
        "area": info["area"],
        "aspect_ratio": info["aspect_ratio"],
        "child_count": info["direct_count"],
        "text_count": info["text_count"],
        "numeric_text_count": info["numeric_count"],
        "has_percentage": any("%" in t for t in texts),
        "has_date_text": info["date_count"] > 0,
        "vector_count": info["vector_count"],
        "line_count": info["line_count"],
        "ellipse_count": info["ellipse_count"],
        "rectangle_count": info["rectangle_count"],
        "graphical_count": info["graphic_count"],
        "text_preview": texts[:10],
        "dashboard": dashboard,
        "candidate_score": score(node, info),
        "has_chart_word": any(
            word in name for word in ("chart", "graph", "trend", "overview", "analytics")
        ),
        "has_table_word": any(
            word in name for word in ("table", "list", "records", "activity", "payment")
        ),
        "has_kpi_word": any(word in name for word in ("kpi", "metric")),
        "has_filter_word": any(
            word in name for word in ("filter", "dropdown", "select", "date picker")
        )
    }


# ============================================================
# REMOVE NESTED CANDIDATES
# ============================================================

def remove_nested(candidates, node_map, children):
    candidate_ids = {c["candidate_id"] for c in candidates}
    kept = []

    for candidate in candidates:
        cid = candidate["candidate_id"]

        if cid not in node_map:
            continue

        ancestors = ancestor_ids(cid, node_map)
        candidate_ancestors = [a for a in ancestors if a in candidate_ids]

        if not candidate_ancestors:
            kept.append(candidate)
            continue

        # The closest candidate ancestor appears first.
        parent_id = candidate_ancestors[0]
        parent = node_map[parent_id]
        parent_info = stats(parent_id, node_map, children)
        child_info = stats(cid, node_map, children)

        parent_name = norm(parent.get("name"))

        if parent_name in {"kpis row", "split row"}:
            kept.append(candidate)
            continue

        # Keep the child if the parent looks like a page-level grouping.
        if (
            parent_info["direct_container_count"] >= 4
            and parent_info["area"] >= 80000
        ):
            kept.append(candidate)
            continue

        if is_internal(node_map[cid]):
            continue

        # Preserve meaningful children rather than a wrapper around them.
        if (
            child_info["area"] >= max(12000, parent_info["area"] * 0.18)
            or (
                strong_component_signal(node_map[cid], child_info) >= 1
                and child_info["area"] >= 8000
                and child_info["text_count"] >= 1
            )
        ):
            kept.append(candidate)

    return kept


# ============================================================
# PROCESS ONE DASHBOARD
# ============================================================

def generate_dashboard(json_path):
    dashboard = os.path.splitext(os.path.basename(json_path))[0]

    print("\n" + "-" * 60)
    print(f"Processing: {dashboard}")
    print(f"Input: {json_path}")
    print("-" * 60)

    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    nodes = load_nodes(data)
    print(f"Found {len(nodes)} Figma nodes.")

    if not nodes:
        print(f"[WARNING] {dashboard} contains no usable nodes.")
        return

    node_map, children = make_maps(nodes)

    # Preserve the special configuration-screen exclusion.
    root_text = " ".join(
        extract_node_text(node)
        for node in nodes
        if node.get("type") == "TEXT"
    ).lower()

    if "13 configurations" in root_text:
        output = {
            "dashboard": dashboard,
            "candidate_count": 0,
            "candidates": []
        }

        output_path = os.path.join(
            OUTPUT_DIR, f"{dashboard}_candidates.json"
        )

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(output, file, indent=2, ensure_ascii=False)

        print(f"[DONE] {dashboard}: 0 candidates (configuration screen)")
        return

    candidates = []
    checked = 0
    rejected = 0

    for node in nodes:
        if not is_container(node):
            continue

        node_id = node.get("id")

        if node_id not in node_map:
            continue

        checked += 1
        info = stats(node_id, node_map, children)

        if is_component_candidate(node, info):
            candidates.append(build_candidate(node, info, dashboard))
        else:
            rejected += 1

    print(f"Containers checked: {checked}")
    print(f"Containers rejected: {rejected}")
    print(f"Raw candidates: {len(candidates)}")

    candidates = remove_nested(candidates, node_map, children)

    # Deduplicate while preserving candidate order.
    unique = {}
    for candidate in candidates:
        unique[candidate["candidate_id"]] = candidate
    candidates = list(unique.values())

    candidates.sort(
        key=lambda candidate: (
            float(candidate.get("y") or 0),
            float(candidate.get("x") or 0)
        )
    )

    output = {
        "dashboard": dashboard,
        "candidate_count": len(candidates),
        "candidates": candidates
    }

    output_path = os.path.join(
        OUTPUT_DIR, f"{dashboard}_candidates.json"
    )

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"\n[DONE] {dashboard}: {len(candidates)} candidates")
    print(f"Saved to: {output_path}")
    print("\nCandidates:")

    for candidate in candidates:
        print(
            f"   - {candidate['candidate_id']} "
            f"| {candidate['name']} "
            f"| type={candidate['type']} "
            f"| size={candidate['width']:.0f}x{candidate['height']:.0f} "
            f"| score={candidate['candidate_score']}"
        )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("GENERATING DASHBOARD COMPONENT CANDIDATES")
    print("=" * 60)
    print(f"\nInput directory:\n{DASHBOARD_DIR}")
    print(f"\nOutput directory:\n{OUTPUT_DIR}")

    if not os.path.isdir(DASHBOARD_DIR):
        print(f"\n[ERROR] Dashboard directory does not exist: {DASHBOARD_DIR}")
        return

    json_files = sorted(
        filename for filename in os.listdir(DASHBOARD_DIR)
        if filename.lower().endswith(".json")
        and os.path.isfile(os.path.join(DASHBOARD_DIR, filename))
    )

    if not json_files:
        print(f"\n[ERROR] No JSON files found in: {DASHBOARD_DIR}")
        return

    print(f"\nFound {len(json_files)} dashboard JSON files.")

    for filename in json_files:
        json_path = os.path.join(DASHBOARD_DIR, filename)

        try:
            generate_dashboard(json_path)
        except Exception as error:
            print(f"\n[ERROR] Failed processing {filename}:")
            print(type(error).__name__, ":", error)

    print("\n" + "=" * 60)
    print("CANDIDATE GENERATION COMPLETE")
    print("=" * 60)
    print(f"Dashboards processed: {len(json_files)}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
