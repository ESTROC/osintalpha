"""Typed, original-preserving question parser for OSINT Alpha.

Design rules (issues 001, 002, 019, 020, 029, 032):

* The analyst's original wording is NEVER discarded or truncated; it is always
  query variant #0 so broad web search sees the full information need.
* Output is a *plan hypothesis*. Nothing here asserts that a person exists,
  is unique, or owns any account. ``attribution_allowed`` is always False.
* Topics, roles, organisations and places are kept as separate, literal,
  UNVERIFIED clues; they are substrings of the question, never inferred.
* A bare given name, or a full name with no discriminating clue, is flagged
  so callers can ask one clarifying question before spending provider quota.

Pure standard library: no FastAPI/httpx/pydantic import, so it is unit-testable
anywhere.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# --- lexicons (lowercase). Small on purpose: unknown words are treated as
# possible name tokens only when they form a clean leading run (see below).
LEAD_PHRASES = (
    'who is', 'who was', 'who are', 'what is', 'tell me about', 'search for',
    'look up', 'find out about', 'find', 'research', 'is', 'does', 'did', 'are',
    'check', 'verify',
)
TOPICS = {
    'cyber', 'cybersecurity', 'security', 'infosec', 'software', 'programming',
    'coding', 'code', 'github', 'linkedin', 'website', 'experience', 'medical',
    'research', 'publication', 'publications', 'startup', 'business', 'sports',
    'robotics', 'hacking', 'malware', 'devops', 'cloud', 'ai', 'dns', 'passive',
    'domain', 'vulnerability', 'advisory', 'electrical', 'plumbing', 'mechanical',
    'repair', 'hardware', 'tutoring', 'marketplace',
}
ROLES = {
    'student', 'plumber', 'electrician', 'developer', 'engineer', 'researcher',
    'professor', 'scientist', 'doctor', 'lawyer', 'teacher', 'contractor',
    'architect', 'tradesperson', 'mechanic', 'carpenter', 'driver', 'officer',
    'analyst', 'consultant', 'founder', 'owner', 'manager', 'intern',
}
ORG_HEADS = {
    'navy', 'army', 'police', 'university', 'college', 'institute', 'school',
    'bank', 'ltd', 'pvt', 'llp', 'inc', 'corp', 'corporation', 'company',
    'ministry', 'hospital', 'iit', 'nit', 'iim', 'trust', 'foundation',
    'academy', 'department',
}
ORG_SUFFIX = {
    'ltd', 'pvt', 'llp', 'llc', 'inc', 'corp', 'corporation', 'company', 'trust',
    'foundation', 'cooperative', 'services', 'works', 'campus', 'club',
    'association', 'society', 'enterprises', 'industries', 'solutions',
    'technologies', 'systems', 'labs', 'park', 'council', 'limited',
}
ORG_MULTI = ('air force',)
NATIONALITY = {'indian', 'british', 'american', 'royal', 'us', 'uk'}
PREPS_ORG = {'at', 'with', 'for'}
PREPS_PLACE = {'in', 'near'}
PREP_EITHER = {'from'}
GENERIC = {
    'public', 'official', 'local', 'published', 'technical', 'review', 'locate',
    'compare', 'list', 'information', 'info', 'details', 'records', 'record',
    'registration', 'schedule', 'portfolio', 'profile', 'about', 'on', 'of',
    'and', 'or', 'the', 'a', 'an', 'to', 'by', 'who', 'where', 'what', 'how',
    'when', 'which', 'related', 'worked', 'working', 'works', 'work', 'was',
    'were', 'be', 'any', 'all', 'please', 'show', 'named', 'search', 'find',
    'tell', 'me', 'his', 'her', 'their', 'has', 'have', 'had', 'participation',
    'city', 'government', 'municipal', 'locality', 'announcement', 'guidance',
    'update', 'document', 'publication', 'policy', 'publicly',
}
LEXICON = TOPICS | ROLES | ORG_HEADS | ORG_SUFFIX | NATIONALITY | PREPS_ORG | PREPS_PLACE \
    | PREP_EITHER | GENERIC | {'air', 'force'}

NAME_TOKEN = re.compile(r"[A-Za-z][A-Za-z'.\-]*")
INITIAL = re.compile(r"[A-Za-z]\.?")
HANDLE = re.compile(r'(?<![\w@])@[A-Za-z0-9_.\-]{2,39}')

IDENTITY_STATES = ('no_person_subject', 'given_name_only',
                   'name_without_clues', 'name_with_unverified_clues')


@dataclass(frozen=True)
class ParsedQuestion:
    original: str
    subject_text: str = ''
    name_tokens: tuple = ()
    topics: tuple = ()
    roles: tuple = ()
    organization_clues: tuple = ()
    location_clues: tuple = ()
    public_handles: tuple = ()
    other_clues: tuple = ()
    identity_state: str = 'no_person_subject'
    needs_clarification: bool = False
    clarification_prompts: tuple = ()
    query_variants: tuple = ()
    attribution_allowed: bool = False  # parser never confirms identity
    notes: tuple = field(default_factory=tuple)

    def as_dict(self):
        out = asdict(self)
        for k, v in list(out.items()):
            if isinstance(v, tuple):
                out[k] = list(v)
        return out


def normalise(text):
    return ' '.join(str(text or '').split())


def _strip_lead(text):
    lowered = text.casefold()
    for phrase in sorted(LEAD_PHRASES, key=len, reverse=True):
        if lowered.startswith(phrase + ' '):
            return text[len(phrase) + 1:].lstrip()
    return text


def _clean(tok):
    return tok.strip(',;:!?()"[]')


def _is_name_token(tok):
    t = _clean(tok)
    if not t or t.casefold() in LEXICON:
        return False
    return bool(NAME_TOKEN.fullmatch(t) and (len(t) >= 2 or INITIAL.fullmatch(t)))


def _titlecase_like(tok):
    t = _clean(tok)
    return bool(t) and t[0].isupper()


def _name_run(tokens, mixed_case):
    """Return (start, end) of the best person-name run, or None.

    Runs are maximal sequences of name-like, non-lexicon tokens (max 4).
    * A run introduced by a place/organisation preposition is a clue, never a
      name ('in Example City').
    * Mixed-case input requires Title-case tokens and may match anywhere.
    * Input with no case signal (all lower / all Title) is accepted only when
      the run starts at the very first token.
    * A run directly followed by an organisation-suffix word ('Ltd', 'Trust',
      'Services') is an organisation name, not a person.
    """
    clue_preps = PREPS_ORG | PREPS_PLACE | PREP_EITHER

    def ok(i):
        return _is_name_token(tokens[i]) and (not mixed_case or _titlecase_like(tokens[i]))

    runs, i = [], 0
    while i < len(tokens):
        if i > 0 and _clean(tokens[i - 1]).casefold() in clue_preps:
            while i < len(tokens) and ok(i):      # skip the whole clue run
                i += 1
            i += 1
            continue
        if ok(i):
            j = i
            while j < len(tokens) and j - i < 4 and ok(j):
                j += 1
            if j < len(tokens) and _clean(tokens[j]).casefold() in ORG_SUFFIX:
                i = j + 1                          # organisation, not a person
                continue
            runs.append((i, j))
            i = j
        else:
            i += 1
    if not mixed_case:
        # No case signal: accept only a leading run that ends the text or is
        # followed by a topic/role/organisation/nationality word. A following
        # plain preposition ('regulatory filing for ...') means it is a phrase.
        follow_ok = TOPICS | ROLES | ORG_HEADS | ORG_SUFFIX | NATIONALITY | {'air'}
        runs = [r for r in runs if r[0] == 0 and (
            r[1] >= len(tokens) or _clean(tokens[r[1]]).casefold() in follow_ok)]
    if not runs:
        return None
    multi = [r for r in runs if r[1] - r[0] >= 2]
    if multi:
        return multi[0]
    return runs[0] if runs[0][0] == 0 else None


def _org_phrase(tokens, idx):
    """Literal organisation phrase around the head word at ``idx``."""
    start = idx
    while start > 0 and _clean(tokens[start - 1]).casefold() in NATIONALITY:
        start -= 1
    end = idx + 1
    # 'IIT Delhi', 'University of X' style: one trailing Title-case token.
    if _clean(tokens[idx]).casefold() in {'iit', 'nit', 'iim'} and end < len(tokens) \
            and _titlecase_like(tokens[end]) and _clean(tokens[end]).casefold() not in LEXICON:
        end += 1
    return start, end


def parse_question(question):
    original = normalise(question)
    text = _strip_lead(original)
    tokens = text.split()
    mixed_case = any(_titlecase_like(t) for t in tokens) and any(
        _clean(t)[:1].islower() for t in tokens if _clean(t))
    # All-Title-case or all-lower inputs carry no case signal.
    all_title = all(_titlecase_like(t) for t in tokens if _clean(t))
    if all_title:
        mixed_case = False

    handles = tuple(dict.fromkeys(HANDLE.findall(original)))
    run = _name_run(tokens, mixed_case)
    name_tokens = tuple(_clean(t) for t in tokens[run[0]:run[1]]) if run else ()

    consumed = set(range(*run)) if run else set()
    topics, roles, orgs, places, other = [], [], [], [], []
    lowered = [_clean(t).casefold() for t in tokens]
    i = 0
    while i < len(tokens):
        low = lowered[i]
        if i in consumed:
            i += 1
            continue
        if low == 'air' and i + 1 < len(tokens) and lowered[i + 1] == 'force':
            start = i
            while start > 0 and lowered[start - 1] in NATIONALITY:
                start -= 1
            orgs.append(' '.join(_clean(t) for t in tokens[start:i + 2]))
            i += 2
            continue
        if low in ORG_HEADS:
            s, e = _org_phrase(tokens, i)
            orgs.append(' '.join(_clean(t) for t in tokens[s:e]))
            i = e
            continue
        if low in TOPICS:
            topics.append(_clean(tokens[i]))
        elif low in ROLES:
            roles.append(_clean(tokens[i]))
        elif low in PREPS_ORG | PREPS_PLACE | PREP_EITHER:
            j = i + 1
            run_toks = []
            while j < len(tokens) and _titlecase_like(tokens[j]) \
                    and lowered[j] not in LEXICON and len(run_toks) < 3:
                run_toks.append(_clean(tokens[j]))
                j += 1
            if run_toks:
                phrase = ' '.join(run_toks)
                if low in PREPS_ORG:
                    orgs.append(phrase)
                elif low in PREPS_PLACE:
                    places.append(phrase)
                else:  # 'from X' is ambiguous: keep as place unless X is an org
                    places.append(phrase)
                i = j
                continue
        elif (run and i > run[1] - 1 and _titlecase_like(tokens[i]) and mixed_case
              and _is_name_token(tokens[i])):
            # Bare trailing Title-case run (e.g. 'plumber Kochi'): a clue whose
            # kind (place vs organisation) we cannot tell. Keep it literal.
            j, run_toks = i, []
            while j < len(tokens) and _titlecase_like(tokens[j]) and _is_name_token(tokens[j]) \
                    and len(run_toks) < 3:
                run_toks.append(_clean(tokens[j]))
                j += 1
            other.append(' '.join(run_toks))
            i = j
            continue
        i += 1

    def uniq(seq):
        return tuple(dict.fromkeys(x for x in seq if x))

    topics, roles, orgs, places = uniq(topics), uniq(roles), uniq(orgs), uniq(places)
    other = uniq(other)
    discriminating = bool(roles or orgs or places or other or handles)

    notes = ['Parsed clues are unverified literal substrings of the question; '
             'they are not confirmed employer, profession, location or handle.']
    prompts = []
    if not name_tokens:
        state = 'no_person_subject'
    elif len(name_tokens) == 1:
        state = 'given_name_only'
        prompts.append('Only a single given name was found. Add a full name, a '
                       'public handle, or a distinguishing organisation/place '
                       'before treating any result as the same person.')
    elif discriminating:
        state = 'name_with_unverified_clues'
        notes.append('Namesakes are still possible; results remain candidates.')
    else:
        state = 'name_without_clues'
        prompts.append('Add one distinguishing clue (organisation, city, role or '
                       'public handle) to separate people who share this name.')

    subject = ' '.join(name_tokens) if len(name_tokens) >= 2 else ''
    variants = [original]
    if subject:
        clue_text = ' '.join(list(topics) + list(orgs) + list(places) + list(other) + list(roles))
        quoted = f'"{subject}"' + (f' {clue_text}' if clue_text else '')
        if quoted != original:
            variants.append(quoted)
        if subject != original and subject not in variants:
            variants.append(subject)
    for h in handles:
        if h not in variants:
            variants.append(h)

    return ParsedQuestion(
        original=original, subject_text=subject, name_tokens=name_tokens,
        topics=topics, roles=roles, organization_clues=orgs, location_clues=places,
        public_handles=handles, other_clues=other, identity_state=state,
        needs_clarification=state in ('given_name_only', 'name_without_clues'),
        clarification_prompts=tuple(prompts), query_variants=tuple(variants[:4]),
        notes=tuple(notes))
