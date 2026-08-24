import difflib


def _actions_by_base_index(base_tokens, other_tokens):
    matcher = difflib.SequenceMatcher(a=base_tokens, b=other_tokens, autojunk=False)
    actions = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset, base_index in enumerate(range(i1, i2)):
                actions[base_index] = ("unchanged", other_tokens[j1 + offset])
        elif tag == "delete":
            for base_index in range(i1, i2):
                actions[base_index] = ("removed", None)
        elif tag == "replace":
            old_len = i2 - i1
            new_len = j2 - j1
            pair_count = min(old_len, new_len)
            for offset in range(pair_count):
                base_index = i1 + offset
                actions[base_index] = ("changed", other_tokens[j1 + offset])
            for base_index in range(i1 + pair_count, i2):
                actions[base_index] = ("removed", None)
    return actions


def diff3_merge(base_tokens, ours_tokens, theirs_tokens):
    ours_actions = _actions_by_base_index(base_tokens, ours_tokens)
    theirs_actions = _actions_by_base_index(base_tokens, theirs_tokens)

    merged_tokens = []
    conflicts = []

    for base_index, base_text in enumerate(base_tokens):
        ours_action, ours_text = ours_actions.get(base_index, ("unchanged", base_text))
        theirs_action, theirs_text = theirs_actions.get(base_index, ("unchanged", base_text))

        if ours_action == "unchanged" and theirs_action == "unchanged":
            merged_tokens.append(base_text)
        elif ours_action == "unchanged":
            if theirs_action == "changed":
                merged_tokens.append(theirs_text)
        elif theirs_action == "unchanged":
            if ours_action == "changed":
                merged_tokens.append(ours_text)
        else:
            if ours_action == "changed":
                merged_tokens.append(ours_text)
            elif theirs_action == "changed":
                merged_tokens.append(theirs_text)

    return {"merged_tokens": merged_tokens, "conflicts": conflicts}
