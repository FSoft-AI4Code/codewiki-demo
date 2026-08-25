# Compiler Parse Utils

## Introduction

This module is the **toolbox of the template parser**. It holds four small, mostly self-contained
files that the parser state machine and the readers call when they need a low-level answer:

| File | Exports | The one question it answers |
| --- | --- | --- |
| `phases/1-parse/utils/html.js` | `decode_character_references`, `get_entity_pattern`, `validate_code` | "What real text does this HTML entity stand for?" |
| `phases/1-parse/utils/bracket.js` | `find_matching_bracket`, `match_bracket` | "Where does this bracket close?" |
| `phases/1-parse/utils/create.js` | `create_fragment` | "Give me an empty child-node container." |
| `phases/1-parse/utils/fuzzymatch.js` | `fuzzymatch` (default), `FuzzySet`, `sort_descending` | "The user typed a bad name — did they mean this one?" |

Two things are worth knowing up front:

- **These helpers hold no parser state.** `html.js`, `create.js` and `fuzzymatch.js` are pure
  functions over strings. Only `match_bracket` touches a `Parser`, and it only *reads*
  `parser.template`.
- **The state machine owns the cursor, not this module.** `find_matching_bracket` and
  `match_bracket` return an index; the caller decides whether to move `parser.index` there.

The parser itself, the cursor, and the state loop live in
[compiler_parse](compiler_parse.md) and [compiler_parse_state_machine](compiler_parse_state_machine.md).

---

## Architecture Overview

### Where the toolbox sits inside phase 1

```mermaid
graph TD
    subgraph phase1["compiler_parse - phase 1"]
        PARSER["Parser class<br/>index.js<br/>cursor and node stack"]

        subgraph sm["compiler_parse_state_machine"]
            FRAG["fragment"]
            TEXT["text"]
            ELEM["element<br/>attributes and directives"]
            TAG["tag<br/>blocks and mustaches"]
        end

        subgraph readers["compiler_parse_readers"]
            EXPR["read_expression"]
            CTX["read_pattern"]
        end

        subgraph utils["compiler_parse_utils - this module"]
            HTML["html.js<br/>decode_character_references"]
            BRK["bracket.js<br/>find_matching_bracket<br/>match_bracket"]
            CRE["create.js<br/>create_fragment"]
            FUZ["fuzzymatch.js<br/>fuzzymatch"]
        end
    end

    ENT["entities.js<br/>2000+ named entities"]
    ERR["errors.js"]
    LATER["phase 2 analyze and phase 3 transform"]

    PARSER --> FRAG
    PARSER --> CRE
    TEXT --> HTML
    ELEM --> HTML
    ELEM --> CRE
    TAG --> CRE
    TAG --> BRK
    EXPR --> BRK
    CTX --> BRK
    HTML --> ENT
    BRK --> ERR
    FUZ --> LATER
    CRE --> LATER
```

Note the odd one out: **`fuzzymatch` has no caller inside phase 1 any more.** It lives in the parse
folder for historical reasons, but today it is imported by
[compiler_analyze](compiler_analyze.md) and by `utils/extract_svelte_ignore.js`
(see [compiler_core](compiler_core.md)).

### Responsibility split

```mermaid
graph LR
    A["character level<br/>html.js"] --> B["token level<br/>bracket.js"]
    B --> C["tree level<br/>create.js"]
    C --> D["diagnostics level<br/>fuzzymatch.js"]

    A -.- A1["turns entity text<br/>into real characters"]
    B -.- B1["finds the end of a<br/>brace, paren or bracket span"]
    C -.- C1["builds the empty Fragment<br/>that child nodes go into"]
    D -.- D1["suggests the name<br/>the user probably meant"]
```

---

## 1. `html.js` — HTML entity decoding

### Purpose

A `.svelte` template is written by humans, so it may contain `&amp;`, `&#8364;` or `&hellip;`.
The compiler does not hand the template to a browser, so nothing decodes those for it. This file
does that job, and it does it **for text nodes and for attribute values only** — never for
expressions or script content.

### The three pieces

| Function | Exported | Job |
| --- | --- | --- |
| `reg_exp_entity` | no | Builds the regex source for **one** entity name, with the attribute-value special case applied |
| `get_entity_pattern` | yes | Joins every entity into **one** big global regex |
| `decode_character_references` | yes | Runs the regex over a string and replaces each hit |
| `validate_code` | yes | Maps a raw code point onto a code point that is legal to emit |

### Why there are two regexes

`get_entity_pattern` is called exactly twice, at module load, and the results are cached in module
constants:

```js
const entity_pattern_content    = get_entity_pattern(false);
const entity_pattern_attr_value = get_entity_pattern(true);
```

Building the pattern is expensive (it walks every key of `entities.js`), so it happens once per
process, not once per template.

The two patterns differ because the HTML spec treats attribute values differently. Inside an
attribute value, an entity **without a trailing semicolon** must *not* decode when the next
character is `=`, a digit, or a letter. `reg_exp_entity` implements that by appending a word
boundary plus a negative lookahead:

| Context | Input | Result |
| --- | --- | --- |
| Text node | `&ampfoo` | decoded — `&` is recognised |
| Attribute value | `?a=1&amp=2` | left alone — `&amp` is followed by `=` |
| Attribute value | `?a=1&amp;b=2` | decoded — the semicolon makes it unambiguous |

This is why every caller must pass the correct `is_attribute_value` flag.

### Decoding flow

```mermaid
flowchart TD
    START["decode_character_references<br/>html, is_attribute_value"] --> PICK{"is_attribute_value"}
    PICK -->|"true"| PA["use entity_pattern_attr_value"]
    PICK -->|"false"| PC["use entity_pattern_content"]
    PA --> REPL["String.replace over every match"]
    PC --> REPL
    REPL --> KIND{"first char of<br/>the captured entity"}
    KIND -->|"not a hash"| NAMED["look the name up in entities.js"]
    KIND -->|"hash then x"| HEX["parseInt base 16"]
    KIND -->|"hash then digits"| DEC["parseInt base 10"]
    NAMED --> CHECK{"code is truthy"}
    HEX --> CHECK
    DEC --> CHECK
    CHECK -->|"no"| KEEP["return the raw match unchanged"]
    CHECK -->|"yes"| VAL["validate_code"]
    VAL --> OUT["String.fromCodePoint"]
```

Two consequences of the `if (!code) return match` line:

- An unknown named entity is **kept verbatim** — the parser never errors on it.
- `&#0;` is also kept verbatim, because `0` is falsy.

### `validate_code` — the code point sanitiser

The compiler writes characters straight into generated output, so it bypasses the browser's own
repair step for illegal code points. `validate_code` performs that repair itself.

| Input code point | Returned | Reason |
| --- | --- | --- |
| `10` (line feed) | `32` (space) | a decoded newline becomes generic whitespace |
| below `128` | unchanged | plain ASCII |
| `128` – `159` | `windows_1252[code - 128]` | browsers lenient-map this range; without the fix a `&#128;` euro sign would vanish |
| `160` – `55295` | unchanged | basic multilingual plane |
| `55296` – `57343` | `0` | UTF-16 surrogate halves are not standalone characters |
| `57344` – `65535` | unchanged | rest of the BMP |
| `65536` – `196607` | unchanged | supplementary multilingual and ideographic planes |
| `917504` – `917631`, `917760` – `917999` | unchanged | supplementary special-purpose plane (tag characters, variation selectors) |
| anything else | `0` | not a usable character |

A `0` result becomes a real NUL character in the output string, which is the same substitution a
browser would make.

### Callers

| Caller | Flag | What gets decoded |
| --- | --- | --- |
| `state/text.js` → `text` | `false` | the `data` of every `Text` node |
| `state/element.js` → `read_static_attribute` | `true` | a quoted or bare static attribute value |
| `state/element.js` → `read_sequence` (via `flush`) | `true` | each plain-text chunk of a mixed attribute value such as `class="a {b} c"` |

All three follow the same convention, which downstream phases rely on:

```mermaid
graph LR
    RAW["node.raw<br/>exactly what the source said<br/>e.g. ampersand a m p semicolon"] --> NODE["Text node"]
    DATA["node.data<br/>decoded value<br/>e.g. a single ampersand"] --> NODE
```

`raw` is preserved so that source maps, the migration tool
([compiler_migrate](compiler_migrate.md)) and error frames can still point at the original text,
while `data` is what actually gets rendered.

---

## 2. `bracket.js` — finding the closing bracket

### Two functions, two contracts

Both functions scan forward for a matching close bracket, but they are built for different
situations and should not be swapped.

| | `find_matching_bracket` | `match_bracket` |
| --- | --- | --- |
| Input | a plain string, a start index, the open char | a `Parser`, a start index, an optional bracket map |
| Assumes the open bracket is | already consumed (`brackets` starts at `1`) | still ahead of `start` (it is pushed on the stack) |
| Returns | index of the close bracket, or `undefined` | index **just past** the close bracket |
| On failure | returns `undefined` quietly | throws a compile error |
| Tracks nesting | one counter for one bracket kind | a stack, so mismatched kinds are detected |
| Skips comments and regex literals | yes | no |
| Main use | loose / error-recovery parsing | strict parsing of patterns and generics |

### `find_matching_bracket` — the forgiving scanner

Its job is to answer "if I cannot parse this expression, where would it have ended?" That is why it
must not be fooled by brackets that live inside strings, comments, or regex literals.

```mermaid
stateDiagram-v2
    [*] --> scan
    scan --> string: quote char, single double or backtick
    scan --> line_comment: slash slash
    scan --> block_comment: slash star
    scan --> regex: slash then anything else
    scan --> count: any other char
    string --> scan: jump past the closing quote
    line_comment --> scan: jump past the newline
    block_comment --> scan: jump past star slash
    regex --> scan: jump past the closing slash
    count --> scan: bump or drop the depth counter
    count --> [*]: depth reaches zero, return the index
    scan --> [*]: end of template, return undefined
```

The private helpers exist to make those jumps safe:

| Helper | Job |
| --- | --- |
| `infinity_if_negative` | turns an `indexOf` miss (`-1`) into `Infinity`, so a failed jump lands past the end of the string and the loop stops instead of walking backwards |
| `find_unescaped_char` | finds the next occurrence of a char that is **not** backslash-escaped |
| `count_leading_backslashes` | counts the run of backslashes before an index; an **even** count means the char is not escaped |
| `find_string_end` | wraps `find_unescaped_char`; for `'` and `"` it first clips the search at the next newline, because a normal string cannot span lines. Backtick strings are searched to the end |
| `find_regex_end` | `find_unescaped_char` looking for the closing slash |

The escape counting is the subtle part:

```mermaid
graph LR
    A["backslash backslash quote"] --> B["two backslashes = even"] --> C["the quote really closes the string"]
    D["backslash quote"] --> E["one backslash = odd"] --> F["the quote is escaped, keep searching"]
```

**Edge cases to be aware of**

- The only caller, `get_loose_identifier`, tests the result with `if (end)`. A close bracket at
  index `0` would therefore be treated as "not found" — harmless in practice, since index `0`
  cannot hold a closing bracket of an expression that started earlier.
- If a `/` is the very last character of the template, `const next_char = template[i + 1]` is
  `undefined` and the `continue` runs **without advancing `i`**. Any change to the `'/'` branch
  should keep this in mind.

### `match_bracket` — the strict scanner

`match_bracket` is used where Svelte genuinely needs a well-formed span before it hands the text to
acorn. It keeps a stack of open brackets, so a wrong closer is an immediate diagnostic rather than a
silently wrong index.

```mermaid
flowchart TD
    START["match_bracket parser, start, brackets"] --> LOOP{"cursor before<br/>end of template"}
    LOOP -->|"no"| EOF["e.unexpected_eof"]
    LOOP -->|"yes"| CH["read one char and advance"]
    CH --> Q{"quote char"}
    Q -->|"yes"| MQ["match_quote"]
    MQ --> LOOP
    Q -->|"no"| OPEN{"char is an<br/>opening bracket"}
    OPEN -->|"yes"| PUSH["push it on the stack"]
    PUSH --> LOOP
    OPEN -->|"no"| CLOSE{"char is a<br/>closing bracket"}
    CLOSE -->|"no"| LOOP
    CLOSE -->|"yes"| POP["pop the stack and compare"]
    POP --> MATCH{"closer matches<br/>the popped opener"}
    MATCH -->|"no"| ETOK["e.expected_token"]
    MATCH -->|"yes"| EMPTY{"stack now empty"}
    EMPTY -->|"no"| LOOP
    EMPTY -->|"yes"| DONE["return the cursor"]
```

`match_quote` handles strings, and it is where the two functions become **mutually recursive**: a
template literal can contain `${ ... }`, and that interpolation can contain another template
literal.

```mermaid
sequenceDiagram
    participant MB as match_bracket
    participant MQ as match_quote
    MB->>MQ: quote char found
    MQ->>MQ: consume chars, honour backslash escapes
    MQ->>MB: backtick string hits dollar brace
    MB->>MQ: nested quote inside the interpolation
    MQ-->>MB: index past the closing quote
    MB-->>MB: continue at the outer level
```

An unterminated string raises `e.unterminated_string_constant` at the position where the string
began, which is the position a developer actually wants to see.

### The `brackets` parameter

`match_bracket` takes a bracket map so the same scanner can be reused for non-JS bracket kinds:

| Caller | Map | Why |
| --- | --- | --- |
| `read/context.js` → `read_pattern` | default: `{}`, `()`, `[]` | isolate a destructuring pattern such as `{ a, b: [c] }` before re-parsing it with acorn |
| `state/tag.js` → snippet parsing | `{ '<': '>' }` (`pointy_bois`) | capture a TypeScript generic signature such as `#snippet foo<T>(...)` |

### Callers in context

```mermaid
graph TD
    LOOSE["read/expression.js<br/>get_loose_identifier"] -->|"expression did not parse,<br/>find where it ends"| FMB["find_matching_bracket"]
    PAT["read/context.js<br/>read_pattern"] -->|"slice out the pattern text"| MB["match_bracket"]
    SNIP["state/tag.js<br/>snippet generics"] -->|"slice out the type params"| MB
```

`get_loose_identifier` is the heart of **loose mode** (used by editor tooling, which must produce a
tree even for half-typed code): when acorn fails, the parser skips to the bracket that
`find_matching_bracket` reports and inserts an empty `Identifier` placeholder. See
[compiler_parse_readers_expression](compiler_parse_readers_expression.md) for the full recovery
story.

---

## 3. `create.js` — the empty fragment factory

`create_fragment` is nine lines long and yet it is called from almost every branch of the state
machine, because **every place that can hold child nodes needs a `Fragment`**.

```js
export function create_fragment(transparent = false) {
    return {
        type: 'Fragment',
        nodes: [],
        metadata: { transparent, dynamic: false, has_await: false }
    };
}
```

### The metadata fields

| Field | Set here | Who consumes it |
| --- | --- | --- |
| `transparent` | by the caller, at parse time | `phases/scope.js` — a transparent fragment does **not** open a new scope of its own (`scope.child(transparent)`); see [compiler_core](compiler_core.md) |
| `dynamic` | always `false` | flipped during analysis (`mark_subtree_dynamic`), read by phase 3 to decide whether a template node needs runtime updates; see [compiler_analyze](compiler_analyze.md) |
| `has_await` | always `false` | filled in during analysis, read by the client transform to wrap a fragment in async plumbing; see [compiler_transform_client](compiler_transform_client.md) |

So the function is really a **schema guarantee**: later phases can assume the metadata object
exists and only ever need to *update* flags, never create them. That is why no call site builds a
fragment literal by hand.

### Who calls it

```mermaid
graph TD
    CF["create_fragment"]
    ROOT["index.js<br/>the Root fragment"] --> CF
    EL["state/element.js<br/>implicit snippet fragments<br/>transparent = true"] --> CF
    IF["state/tag.js<br/>if consequent and alternate"] --> CF
    EACH["state/tag.js<br/>each body and fallback"] --> CF
    AW["state/tag.js<br/>await pending, then, catch"] --> CF
    KEY["state/tag.js<br/>key body"] --> CF
    SNIP["state/tag.js<br/>snippet body"] --> CF
```

`index.js` also pushes the root fragment onto `parser.fragments`, the stack that `parser.append`
writes into — so this factory produces the very first container the parser ever uses. Details of
that stack are in [compiler_parse](compiler_parse.md).

---

## 4. `fuzzymatch.js` — "did you mean …?"

### Purpose

When a developer writes `bind:valu` or `aria-lable`, an error that only says "unknown name" is
unhelpful. `fuzzymatch(name, names)` returns the closest known name, or `null` if nothing is close
enough:

```js
const match = fuzzymatch(node.name, Object.keys(binding_properties));
```

The gate is deliberately strict — only a score **above 0.7** counts:

```js
return matches && matches[0][0] > 0.7 ? matches[0][1] : null;
```

A bad suggestion is worse than none, so near-misses are dropped.

### The algorithm

The file is an adaptation of `fuzzyset.js` (BSD licensed). It is a **two-stage** matcher: a cheap
n-gram search narrows the field, then an exact edit distance ranks the survivors.

```mermaid
flowchart TD
    IN["fuzzymatch name, names"] --> EMPTY{"names is empty"}
    EMPTY -->|"yes"| NULL1["return null"]
    EMPTY -->|"no"| BUILD["new FuzzySet names<br/>index every name at gram size 2 and 3"]
    BUILD --> GET["set.get name"]
    GET --> EXACT{"lowercase name is<br/>in exact_set"}
    EXACT -->|"yes"| SCORE1["score 1, return immediately"]
    EXACT -->|"no"| TRY["try gram size 3, then 2"]
    TRY --> CAND["stage 1: cosine similarity<br/>over shared grams"]
    CAND --> TRUNC["sort, keep the top 50"]
    TRUNC --> LEV["stage 2: rescore with<br/>1 minus normalised levenshtein"]
    LEV --> TOP["keep every entry tied<br/>with the best score"]
    TOP --> GATE{"best score above 0.7"}
    SCORE1 --> GATE
    GATE -->|"yes"| OUT["return the matching name"]
    GATE -->|"no"| NULL2["return null"]
```

### The `FuzzySet` data structures

| Field | Shape | Role |
| --- | --- | --- |
| `exact_set` | lowercase name → original name | O(1) exact hit, and the way the original casing is restored at the end |
| `items[gram_size]` | array of `[vector_normal, lowercase_name]` | per-name vector length, used as the denominator of the cosine score |
| `match_dict[gram]` | array of `[item_index, gram_count]` | inverted index: given a gram, which names contain it and how often |

Indexing detail: `iterate_grams` lowercases the value, strips non-word characters, and wraps it in
hyphens (`value` becomes `-value-`), so grams at the start and end of a name are weighted like any
other. Each name is indexed twice, at gram size 2 and gram size 3.

```mermaid
graph LR
    NAME["value"] --> WRAP["hyphen value hyphen"]
    WRAP --> G["grams of size 3<br/>hyphen v a, v a l, a l u, l u e, u e hyphen"]
    G --> COUNT["gram_counter<br/>gram to occurrence count"]
    COUNT --> INV["match_dict<br/>gram to name list"]
    COUNT --> NORM["vector_normal<br/>square root of the sum of squares"]
```

### Helpers

| Helper | Exported | Job |
| --- | --- | --- |
| `levenshtein` | no | classic edit distance, computed with a single rolling row |
| `_distance` | no | `1 - distance / max(len1, len2)` — turns edit distance into a 0-to-1 similarity |
| `iterate_grams` | no | splits a name into overlapping n-grams |
| `gram_counter` | no | counts gram occurrences |
| `sort_descending` | yes | comparator on the score of a `[score, name]` tuple; used for both sort passes |

`sort_descending` is exported mainly so tooling can reference it; inside the file it is the shared
comparator for the candidate list and for the rescored list.

### Why the two-stage design

Stage 1 is cheap and recall-oriented: an inverted-index lookup avoids comparing the typo against
every candidate. Stage 2 is precise but quadratic in string length, so it is applied only to the
top 50 candidates. The `GRAM_SIZE_UPPER` → `GRAM_SIZE_LOWER` fallback loop handles short names,
where 3-grams may produce no candidates at all but 2-grams still do.

### Where suggestions surface

| Call site | Suggests | Diagnostic |
| --- | --- | --- |
| `2-analyze/visitors/BindDirective.js` | a valid binding name | `bind_invalid_name` |
| `2-analyze/visitors/shared/a11y/index.js` | an ARIA attribute, or an ARIA role | `a11y_unknown_aria_attribute`, `a11y_unknown_role` |
| `utils/extract_svelte_ignore.js` | a real warning code inside `svelte-ignore` | `unknown_code` |

See [compiler_analyze](compiler_analyze.md) and
[compiler_options_and_warnings](compiler_options_and_warnings.md) for how those messages are
emitted.

---

## Cross-cutting concerns

### End-to-end data flow

```mermaid
flowchart LR
    SRC[".svelte source text"] --> P["Parser cursor loop"]
    P --> F["fragment dispatcher"]
    F --> T["text state"]
    F --> E["element state"]
    F --> G["tag state"]

    T --> H1["decode_character_references<br/>flag false"]
    E --> H2["decode_character_references<br/>flag true"]
    E --> C1["create_fragment"]
    G --> C2["create_fragment"]
    G --> B1["match_bracket<br/>snippet generics"]

    G --> RE["read_expression"]
    E --> RE
    RE --> B2["find_matching_bracket<br/>loose mode only"]
    G --> RP["read_pattern"]
    RP --> B3["match_bracket"]

    H1 --> AST["AST"]
    H2 --> AST
    C1 --> AST
    C2 --> AST
    B1 --> AST
    B2 --> AST
    B3 --> AST

    AST --> AN["phase 2 analyze"]
    AN --> FZ["fuzzymatch<br/>only on the error path"]
    AN --> TR["phase 3 transform"]
```

The picture makes the module's two lifetimes clear: `html.js`, `bracket.js` and `create.js` run on
the **happy path**, once per matching construct; `fuzzymatch.js` runs only when something is already
wrong.

### Error handling

| Function | Failure mode |
| --- | --- |
| `decode_character_references` | never fails; unrecognised input is returned verbatim |
| `find_matching_bracket` | returns `undefined`; the caller decides what to do |
| `match_bracket` | throws `expected_token`, `unexpected_eof`, or `unterminated_string_constant` from `errors.js` |
| `create_fragment` | cannot fail |
| `fuzzymatch` | returns `null` when nothing scores above 0.7 |

Only `bracket.js` imports `errors.js`, and only `match_bracket` throws. That is what makes
`find_matching_bracket` usable for loose mode, where throwing would defeat the purpose.

### Dependencies

```mermaid
graph TD
    subgraph mod["compiler_parse_utils"]
        HTML["html.js"]
        BRK["bracket.js"]
        CRE["create.js"]
        FUZ["fuzzymatch.js"]
    end

    ENT["1-parse/utils/entities.js<br/>data table"]
    ERR["compiler/errors.js"]
    TYP["AST.Fragment type<br/>see compiler_ast_types"]

    HTML --> ENT
    BRK --> ERR
    BRK -.->|"type only"| PARSER["Parser class"]
    CRE -.->|"type only"| TYP
    FUZ --> NONE["no imports"]
```

The dependency surface is intentionally tiny: one data table, one error module, and type-only
imports. Nothing here imports another phase, which is why the helpers can be reused freely — and
why `fuzzymatch` can be imported by phase 2 without creating a cycle.

### Performance notes

| Cost | Where |
| --- | --- |
| Two big regexes built once per process | `get_entity_pattern` at module load in `html.js` |
| One `FuzzySet` built **per call** | `fuzzymatch` — acceptable because it only runs on the error path |
| Linear single pass, no backtracking | both bracket scanners |
| One tiny object allocation per container | `create_fragment` |

If `fuzzymatch` ever moves onto a hot path, the per-call `FuzzySet` construction is the first thing
to cache.

---

## Working with this module

**Adding or changing entity behaviour.** Entity names live in `entities.js`, not in `html.js`.
Changing the attribute-value rule means changing `reg_exp_entity`, and the change affects every
attribute in every component — the two cached patterns are shared process-wide.

**Adding a new bracket kind.** Prefer passing a map to `match_bracket` (as `pointy_bois` does) over
writing a new scanner. `find_matching_bracket`'s `default_brackets` table is only consulted for the
closer of the *given* opener, so it stays single-kind by design.

**Adding a new block or container node.** Always build its child list with `create_fragment`, and
pass `transparent: true` only when the construct should **not** introduce its own scope.

**Adding a "did you mean" hint.** Call `fuzzymatch(bad_name, list_of_valid_names)` and pass the
result straight into the warning or error builder; the `null` case is already the "no suggestion"
signal that the message templates expect.

---

## Related documentation

| Document | Relationship |
| --- | --- |
| [compiler_parse](compiler_parse.md) | the `Parser` class, the cursor primitives, and the phase-1 entry point |
| [compiler_parse_state_machine](compiler_parse_state_machine.md) | the states that call `decode_character_references` and `create_fragment` |
| [compiler_parse_state_machine_dispatch](compiler_parse_state_machine_dispatch.md) | `fragment` and `text`, the main users of entity decoding |
| [compiler_parse_state_machine_element](compiler_parse_state_machine_element.md) | attribute reading, the second user of entity decoding |
| [compiler_parse_state_machine_tag](compiler_parse_state_machine_tag.md) | block parsing, snippet generics, and fragment creation |
| [compiler_parse_readers_expression](compiler_parse_readers_expression.md) | loose-mode recovery via `find_matching_bracket`, patterns via `match_bracket` |
| [compiler_parse_js_interop](compiler_parse_js_interop.md) | the acorn wrapper whose failures trigger loose mode |
| [compiler_analyze](compiler_analyze.md) | consumes fragment metadata and calls `fuzzymatch` for suggestions |
| [compiler_ast_types](compiler_ast_types.md) | the `AST.Fragment` and `AST.Text` shapes produced here |
| [compiler_core](compiler_core.md) | scope creation (`transparent`) and `extract_svelte_ignore` |
