#!/usr/bin/env python3
import tomli
import sys


def get_nested_value(data, keys):
    """Safely get nested value from dict using list of keys"""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def python_to_system_deps(python_deps):
    mapping = {
        "mysqlclient": "python3-mysqldb",
        "pillow": "python3-pil",
        "psycopg2-binary": "python3-psycopg2",
        "psycopg2": "python3-psycopg2",
        "pyyaml": "python3-yaml",
        # Add more mappings as needed
    }

    system_deps = ["python3"]
    for dep in python_deps:
        if dep in mapping:
            system_deps.append(mapping[dep])
        else:
            # Fallback: try python3- prefix
            system_deps.append(f"python3-{dep}")

    return "--depends " + " --depends ".join(system_deps)


if len(sys.argv) != 3:
    print("Usage: extract_pyproject.py <pyproject.toml> <field>")
    print("Fields can be nested using dots, e.g.: project.urls.Homepage")
    sys.exit(1)

try:
    with open(sys.argv[1], "rb") as f:
        data = tomli.load(f)

    field = sys.argv[2]

    # Handle dotted notation (e.g., "project.urls.Homepage")
    if "." in field:
        keys = field.split(".")
        value = get_nested_value(data, keys)
    else:
        # Simple lookup for root-level fields
        value = data.get(field)

    # Special handling for an author array
    if field == "project.authors" and value and isinstance(value, list):
        # Format authors as "Name <email>"
        formatted_authors = []
        for author in value:
            if isinstance(author, dict):
                name = author.get("name", "")
                email = author.get("email", "")
                if name and email:
                    formatted_authors.append(f"{name} <{email}>")
                elif name:
                    formatted_authors.append(name)
                elif email:
                    formatted_authors.append(email)
            elif isinstance(author, str):
                formatted_authors.append(author)

        if formatted_authors:
            value = ", ".join(formatted_authors)

    if field == "project.dependencies" and value and isinstance(value, list):
        value = python_to_system_deps(value)

    if value:
        print(value)
    else:
        print(f"Field '{field}' not found in pyproject.toml", file=sys.stderr)
        sys.exit(1)

except FileNotFoundError:
    print(f"Error: File {sys.argv[1]} not found", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
