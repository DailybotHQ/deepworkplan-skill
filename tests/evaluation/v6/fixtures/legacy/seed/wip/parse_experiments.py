"""User WIP experiments — deliberately incomplete. Do not touch.

Idea: parse a line honoring double-quoted fields with embedded delimiters.
Not finished: quoting/escaping does not round-trip yet.
"""


def try_parse_quoted(line, delimiter=","):
    fields = []
    current = ""
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if ch == delimiter and not in_quotes:
            fields.append(current)
            current = ""
            continue
        current += ch
    fields.append(current)
    # TODO(user): handle doubled quotes inside quoted fields
    # TODO(user): handle trailing newline artifact
    return fields
