import difflib


def _actions_by_base_index(base_tokens, other_tokens):
    matcher = difflib.SequenceMatcher(a=base_tokens, b=other_tokens, autojunk=False)
    actions = {}
    insertions = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset, base_index in enumerate(range(i1, i2)):
                actions[base_index] = ("unchanged", other_tokens[j1 + offset])
        elif tag == "delete":
            for base_index in range(i1, i2):
                actions[base_index] = ("removed", None)
        elif tag == "insert":
            insertions.setdefault(i1, []).extend(other_tokens[j1:j2])
        elif tag == "replace":
            old_len = i2 - i1
            new_len = j2 - j1
            pair_count = min(old_len, new_len)
            for offset in range(pair_count):
                base_index = i1 + offset
                actions[base_index] = ("changed", other_tokens[j1 + offset])
            for base_index in range(i1 + pair_count, i2):
                actions[base_index] = ("removed", None)
            if new_len > pair_count:
                insertions.setdefault(i1 + pair_count, []).extend(other_tokens[j1 + pair_count:j2])
    return actions, insertions


def diff3_merge(base_tokens, ours_tokens, theirs_tokens):
    ours_actions, ours_insertions = _actions_by_base_index(base_tokens, ours_tokens)
    theirs_actions, theirs_insertions = _actions_by_base_index(base_tokens, theirs_tokens)

    merged_tokens = []
    conflicts = []

    for base_index, base_text in enumerate(base_tokens):
        for token in ours_insertions.get(base_index, []):
            merged_tokens.append(token)
        for token in theirs_insertions.get(base_index, []):
            if token not in ours_insertions.get(base_index, []):
                merged_tokens.append(token)

        ours_action, ours_text = ours_actions.get(base_index, ("unchanged", base_text))
        theirs_action, theirs_text = theirs_actions.get(base_index, ("unchanged", base_text))

        if ours_action == "unchanged" and theirs_action == "unchanged":
            merged_tokens.append(base_text)
        elif ours_action == "unchanged" and theirs_action != "unchanged":
            if theirs_action == "changed":
                merged_tokens.append(theirs_text)
        elif theirs_action == "unchanged" and ours_action != "unchanged":
            if ours_action == "changed":
                merged_tokens.append(ours_text)
        else:
            if ours_action == theirs_action and ours_text == theirs_text:
                if ours_action == "changed":
                    merged_tokens.append(ours_text)
            else:
                # Append the base text as a placeholder so callers can resolve
                # a conflict (e.g. the merge-request flow) by overwriting
                # merged_tokens[position] with the resolved text. `position`
                # must be the actual list index the placeholder will occupy in
                # merged_tokens -- NOT base_index -- because merged_tokens is
                # not index-aligned with base_tokens whenever insertions or
                # deletions have occurred earlier in the loop. Capturing
                # len(merged_tokens) right before the append is correct
                # because every earlier base position's tokens (including any
                # insertions) have already been appended by this point.
                position = len(merged_tokens)
                merged_tokens.append(base_text)
                conflicts.append({
                    "position": position,
                    "base": base_text,
                    "ours": ours_text if ours_action == "changed" else None,
                    "theirs": theirs_text if theirs_action == "changed" else None,
                })

    trailing_index = len(base_tokens)
    for token in ours_insertions.get(trailing_index, []):
        merged_tokens.append(token)
    for token in theirs_insertions.get(trailing_index, []):
        if token not in ours_insertions.get(trailing_index, []):
            merged_tokens.append(token)

    return {"merged_tokens": merged_tokens, "conflicts": conflicts}
