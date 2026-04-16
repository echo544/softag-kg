# SOFTagKG — CLI for queries on the KG
# 1) queries 1-6 from report (presets)
# 2) tag lookup
# 3) custom SPARQL input

from rdflib import Graph, Namespace, RDF, RDFS
from pathlib import Path
import sys
import textwrap

SOF = Namespace("https://softagkg.org/ontology#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
TTL_PATH = Path(__file__).parent / "output" / "softagkg.ttl"

def print_table(headers, rows, col_widths):
    if not rows:
        print("  (no results)")
        return
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print("  " + "  ".join("─" * w for w in col_widths))
    for row in rows:
        truncated = []
        for i, cell in enumerate(row):
            s = str(cell)
            truncated.append(s[:col_widths[i]-1] + "…" if len(s) > col_widths[i] else s)
        print(fmt.format(*truncated))
    print(f"\n  {len(rows)} result(s)")

# presets (1-6 from queries.py for demo purposes)

PRESETS = {
    "1": {
        "name": "Top 10 co-occurring tags with Python (by weight)",
        "description": "Which technologies are most strongly associated with Python on Stack Overflow?",

        "sparql": """
PREFIX sof:  <https://softagkg.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?partnerLabel ?weight
WHERE {
    {
        ?cooc sof:source   sof:python ;
              sof:target   ?partner ;
              sof:coWeight ?weight .
    } UNION {
        ?cooc sof:source   ?partner ;
              sof:target   sof:python ;
              sof:coWeight ?weight .
    }
    ?partner rdfs:label ?partnerLabel .
}

ORDER BY DESC(?weight)

LIMIT 10""",

        "headers": ["Tag", "Co-occurrences"],
        "widths":  [28, 18],
        "fields":  ["partnerLabel", "weight"],
        "format":  [str, lambda x: f"{int(x):,}"]
    },
    "2": {
        "name": "All synonym pairs (skos:exactMatch)",
        "description": "Which tags have official Stack Overflow synonym mappings within the top 250?",

        "sparql": """
PREFIX sof:  <https://softagkg.org/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sourceLabel ?targetLabel
WHERE {
    ?source skos:exactMatch ?target .
    ?source rdfs:label      ?sourceLabel .
    ?target rdfs:label      ?targetLabel .
}

ORDER BY ?sourceLabel""",
        "headers": ["Alias", "Canonical tag"],
        "widths":  [28, 28],
        "fields":  ["sourceLabel", "targetLabel"],
        "format":  [str, str]
    },

    "3": {
        "name": "Comparative bridge query: Docker + Python vs Docker + Kubernetes",
        "description": "Compares bridge tags across two anchor-pair scenarios in one query.",

        "sparql": """
PREFIX sof:  <https://softagkg.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?scenario ?bridgeLabel ?bridgeCount
WHERE {
    VALUES (?a ?b ?scenario ?order) {
        (sof:docker sof:python "Docker + Python" 1)
        (sof:docker sof:kubernetes "Docker + Kubernetes" 2)
    }

    ?a sof:coOccursWith ?bridge .
    ?b sof:coOccursWith ?bridge .
    ?bridge rdfs:label ?bridgeLabel .
    ?bridge sof:questionCount ?bridgeCount .

    FILTER(?bridge != ?a && ?bridge != ?b)
}

ORDER BY ?order DESC(?bridgeCount)""",

        "headers": ["Scenario", "Bridge Tag", "Question Count"],
        "widths":  [24, 28, 16],
        "fields":  ["scenario", "bridgeLabel", "bridgeCount"],
        "format":  [str, str, lambda x: f"{int(x):,}"]
    },

    "4": {
        "name": "Top 15 tags with no synonym mapping (gap detection)",
        "description": "Which high-traffic tags have no formal synonym recorded in the graph?",

        "sparql": """
PREFIX sof:  <https://softagkg.org/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?tagLabel ?questionCount
WHERE {
    ?tag a                 sof:Tag .
    ?tag rdfs:label        ?tagLabel .
    ?tag sof:questionCount ?questionCount .
    FILTER NOT EXISTS {
        { ?tag   skos:exactMatch ?other }
        UNION
        { ?other skos:exactMatch ?tag  }
    }
}

ORDER BY DESC(?questionCount)

LIMIT 15""",

        "headers": ["Tag", "Question Count"],
        "widths":  [28, 16],
        "fields":  ["tagLabel", "questionCount"],
        "format":  [str, lambda x: f"{int(x):,}"]
    },
    "5": {
        "name": "Tags with over 500,000 questions with descriptions",
        "description": "What are the most-used technologies on Stack Overflow and what do they do?",

        "sparql": """
PREFIX sof:  <https://softagkg.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?tagLabel ?questionCount ?description
WHERE {
    ?tag a                 sof:Tag .
    ?tag rdfs:label        ?tagLabel .
    ?tag sof:questionCount ?questionCount .
    ?tag rdfs:comment      ?description .
    FILTER(?questionCount > 500000)
}

ORDER BY DESC(?questionCount)""",

        "headers": ["Tag", "Questions", "Description"],
        "widths":  [14, 12, 70],
        "fields":  ["tagLabel", "questionCount", "description"],
        "format":  [str, lambda x: f"{int(x):,}", str]
    },
    "6": {
        "name": "Multi-anchor weighted recommendation query",
        "description": "Given Docker, Nginx, and PostgreSQL, retrieves tags linked to at least two anchors and ranks them by breadth and weight.",

        "sparql": """
PREFIX sof:  <https://softagkg.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?candLabel
    (COUNT(DISTINCT ?anchor) AS ?supportedBy)
    (SUM(?w) AS ?totalWeight)
    (MAX(?candCount) AS ?candCount)
WHERE {
    VALUES ?anchor { sof:docker sof:nginx sof:postgresql }

    ?cooc a sof:CoOccurrence ;
        sof:coWeight ?w .

    {
        ?cooc sof:source ?anchor ;
            sof:target ?cand .
    }

    UNION

    {
        ?cooc sof:source ?cand ;
            sof:target ?anchor .
    }

    FILTER(?cand NOT IN (sof:docker, sof:nginx, sof:postgresql))

    ?cand rdfs:label ?candLabel ;
        sof:questionCount ?candCount .
}

GROUP BY ?cand ?candLabel
HAVING (COUNT(DISTINCT ?anchor) >= 2)

ORDER BY DESC(?supportedBy) DESC(?totalWeight)

LIMIT 15""",

        "headers": ["Recommended Tag", "Supported By", "Total Weight", "Question Count"],
        "widths":  [28, 14, 15, 16],
        "fields":  ["candLabel", "supportedBy", "totalWeight", "candCount"],
        "format":  [str, lambda x: f"{int(x)}", lambda x: f"{int(x):,}", lambda x: f"{int(x):,}"]
    },
}

# tag lookup

def tag_lookup(g, tag_name):
    tag_name = tag_name.strip().lower()
    safe = (tag_name.replace("+", "plus").replace(".", "dot").replace("#", "sharp").replace(" ", "-"))
    uri = SOF[safe]
    label = g.value(uri, RDFS.label)

    if not label:
        print(f"\n  Tag '{tag_name}' not found in KG")
        print("  Check spelling or try exact Stack Overflow tag name (eg. 'c++', 'node.js', etc.)")
        return

    count = g.value(uri, SOF.questionCount)
    desc = g.value(uri, RDFS.comment)
    synonyms = list(g.objects(uri, SKOS.exactMatch)) + list(g.subjects(SKOS.exactMatch, uri))

    # co-occurrence neighbors (both directions between target and source, using CoOccurrence nodes)
    neighbors = []
    for cooc in g.subjects(SOF.source, uri):
        tgt = g.value(cooc, SOF.target)
        wt = g.value(cooc, SOF.coWeight)
        if tgt and wt:
            neighbors.append((str(g.value(tgt, RDFS.label)), int(wt)))
    for cooc in g.subjects(SOF.target, uri):
        src = g.value(cooc, SOF.source)
        wt = g.value(cooc, SOF.coWeight)
        if src and wt:
            neighbors.append((str(g.value(src, RDFS.label)), int(wt)))
    neighbors.sort(key=lambda x: x[1], reverse=True)

    print(f"Tag: {label}")
    print(f"  Question count:  {int(count):,}")
    if desc:
        wrapped = textwrap.fill(str(desc), width=70, initial_indent="  ", subsequent_indent="  ")
        print(f"  Description:    \n{wrapped}")
    if synonyms:
        syn_labels = [str(g.value(s, RDFS.label)) for s in synonyms]
        print(f"  Synonyms:        {', '.join(syn_labels)}")
    else:
        print(f"  Synonyms:        none in top 250 tags")

    print(f"\n  Co-occurrence degree:  {len(neighbors)} tags")
    if neighbors:
        print(f"\n  Top 10 co-occurring tags:")
        print_table(
            ["Tag", "Co-occurrences"],
            [(n, f"{w:,}") for n, w in neighbors[:10]],
            [28, 18]
        )

# custom query (SPARQL)

def run_custom_sparql(g):
    print("\n  Enter custom SPARQL query. Type END on a new line when done.")
    print("  Available prefixes:")
    print("    PREFIX sof:  <https://softagkg.org/ontology#>")
    print("    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>")
    print("    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>")
    print("    PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>")
    print()
    
    lines = []
    while True:
        line = input("  > ")
        if line.strip().upper() == "END":
            break
        lines.append(line)
    query = "\n".join(lines)
    if not query.strip():
        print("  (empty query)")
        return
    try:
        results = list(g.query(query))
        if not results:
            print("\n  (no results)")
            return
        # Print raw results
        print(f"\n  {len(results)} result(s):\n")
        vars_ = [str(v) for v in results[0].labels]
        widths = [max(len(v), 18) for v in vars_]
        fmt = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
        print(fmt.format(*vars_))
        print("  " + "  ".join("─" * w for w in widths))
        for row in results:
            vals = [str(getattr(row, v, "")) for v in vars_]
            print(fmt.format(*[v[:w-1]+"…" if len(v)>w else v
                               for v, w in zip(vals, widths)]))
    except Exception as e:
        print(f"\n  SPARQL error: {e}")

# query presets

def run_preset(g, key):
    preset = PRESETS[key]
    print(f"Query {key}: {preset['name']}")
    print(f"  {preset['description']}\n")
    results = list(g.query(preset["sparql"]))
    rows = []
    for r in results:
        row = []
        for field, fmt in zip(preset["fields"], preset["format"]):
            row.append(fmt(getattr(r, field)))
        rows.append(row)
    print_table(preset["headers"], rows, preset["widths"])

# REPL

def main():
    print("SOFTagKG — Interactive Query Interface")
    if not TTL_PATH.exists():
        print("  Run build_graph.py first.")
        sys.exit(1)

    g = Graph()
    g.parse(str(TTL_PATH), format="turtle")
    n_tags = len(list(g.subjects(RDF.type, SOF.Tag)))
    n_cooc = len(list(g.subjects(RDF.type, SOF.CoOccurrence)))
    n_trip = len(g)

    while True:
        print("SOFTagKG — Main Menu")
        print("  Query presets:")
        for k, v in PRESETS.items():
            print(f"    [{k}] {v['name']}")
        print()
        print("  Other options:")
        print("    [l] Look up a specific tag")
        print("    [s] Enter custom SPARQL query")
        print("    [q] Quit")
        print()
        choice = input("  Enter choice (char): ").strip().lower()
        if choice == "q":
            print("\n  Exit selected.\n")
            break
        elif choice == "l":
            tag = input("\n  Enter tag name: ").strip()
            tag_lookup(g, tag)
        elif choice == "s":
            run_custom_sparql(g)
        elif choice in PRESETS:
            run_preset(g, choice)
        else:
            print("\n  Unrecognised option, please try again.")

        input("\n  Press ENTER key to return to main menu.")

if __name__ == "__main__":
    main()