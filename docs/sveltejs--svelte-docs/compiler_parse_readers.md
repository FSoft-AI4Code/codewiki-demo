# compiler_parse_readers

## 1. What This Module Is

The **readers** are the part of Svelte's template parser that handle everything
which is *not* plain HTML markup.

Svelte's `.svelte` file is a mix of four different languages:

| Language | Where it appears | Who reads it |
| --- | --- | --- |
| HTML-like markup | anywhere | the state machine (see [compiler_parse_state_machine](compiler_parse_state_machine.md)) |
| JavaScript / TypeScript **expressions** | `{...}`, attribute values, block heads | `read/expression.js` |
| JavaScript / TypeScript **patterns** | `{#each list as x}`, `{:then x}` | `read/context.js` |
| A whole JS/TS **program** | `<script>` | `read/script.js` |
| **CSS** | `<style>` | `read/style.js` |
| A small config **DSL** | `<svelte:options>` | `read/options.js` |

Each reader is a small, focused function. The state machine walks the template
character by character; the moment it hits a region written in another language,
it hands control to a reader. The reader consumes that region, produces an AST
node, moves the parser's cursor (`parser.index`) past the region, and returns.

So the simple mental model is:

> **The state machine decides *where* something starts. A reader decides *what*
> it is and *where it ends*.**

### Why the readers are separate from the state machine

Three reasons:

1. **Different grammars.** You cannot parse CSS with an HTML tokenizer, and you
   cannot parse JavaScript with either. Each reader owns one grammar.
2. **Different tools.** Expression/pattern/script readers delegate to Acorn (a
   real JS parser). The style reader is a hand-written CSS parser. Keeping them
   apart keeps each one small.
3. **Error recovery.** Editors (the Svelte language server) parse *broken* code
   all day. The readers hold the logic that turns a hard parse failure into a
   soft placeholder node, so an editor can still get a usable tree.

---

## 2. Where the Module Sits

```mermaid
graph TD
    subgraph Input
        SRC["dot-svelte source text"]
    end

    subgraph P1["Phase 1 &mdash; parse"]
        PARSER["Parser<br/>(cursor + helpers)"]
        SM["State machine<br/>fragment / element / tag / text"]
        RD["<b>readers</b><br/>expression, context,<br/>script, style, options"]
        JS["JS interop<br/>(Acorn wrapper)"]
        UT["parse utils<br/>(bracket, html, fuzzymatch)"]
    end

    subgraph Downstream
        AN["Phase 2 &mdash; analyze"]
        TR["Phase 3 &mdash; transform"]
    end

    SRC --> PARSER
    PARSER --> SM
    SM -->|"hands off non-HTML regions"| RD
    RD -->|"AST nodes + new cursor"| SM
    RD --> JS
    RD --> UT
    SM --> AST["AST.Root"]
    AST --> AN --> TR

    click SM "compiler_parse_state_machine.md"
    click JS "compiler_parse_js_interop.md"
    click UT "compiler_parse_utils.md"
```

Related modules:

- [compiler_parse](compiler_parse.md) — the parent module; owns the `Parser`
  class and the overall phase-1 entry point.
- [compiler_parse_state_machine](compiler_parse_state_machine.md) — the caller
  of every reader.
- [compiler_parse_js_interop](compiler_parse_js_interop.md) — the Acorn wrapper
  (`parse`, `parse_expression_at`, comment handling, TypeScript stripping) that
  three of the five readers depend on.
- [compiler_parse_utils](compiler_parse_utils.md) — bracket matching, HTML
  entity decoding, fuzzy matching.
- [compiler_ast_types](compiler_ast_types.md) — the shape of every node the
  readers build.
- [compiler_options_and_warnings](compiler_options_and_warnings.md) — the
  compile-level option schema, which is a different thing from the per-component
  `<svelte:options>` handled here.

---

## 3. The Shared Contract

Every reader follows the same three-part contract. Understanding it once means
understanding all five.

```mermaid
sequenceDiagram
    participant SM as State machine
    participant R as Reader
    participant P as Parser (cursor)
    participant A as Acorn / hand-written scanner

    SM->>R: call reader(parser, ...)
    R->>P: read parser.index, parser.template
    R->>A: parse the sub-language
    alt success
        A-->>R: AST node with start/end
        R->>P: parser.index = node.end
        R-->>SM: node
    else failure
        A-->>R: throw
        alt parser.loose (editor mode)
            R->>P: skip to matching bracket
            R-->>SM: placeholder node
        else strict (compile mode)
            R->>P: parser.acorn_error(err)
            Note over R,SM: raises a compile error
        end
    end
```

**The three invariants:**

1. **Input** is always `(parser, ...extras)`. The reader takes the whole parser,
   not just a string, because it needs the cursor, the template, the TS flag,
   and the shared comment array.
2. **Cursor discipline.** On return, `parser.index` must point at the first
   character *after* the consumed region. Everything downstream depends on this.
3. **Positions are absolute.** Every node carries `start` / `end` offsets into
   the *original* source, even when the reader had to feed Acorn a rewritten
   string. Keeping offsets honest is what makes source maps and editor
   diagnostics work — and it is the single trickiest part of this module.

### The offset-preservation trick

`read_pattern` and `read_type_annotation` cannot hand raw text to Acorn, because
`{ y = z }` alone is not a valid expression and `: string` alone is not valid at
all. The fix is to build a **synthetic source string** that:

- pads the front with whitespace of the exact same length as the real prefix
  (newlines preserved, so line numbers stay correct), and
- wraps the fragment in just enough syntax to make Acorn accept it
  (`(pattern = 1)` for patterns, `_ as <type>` for annotations),

then parses at the original offset and unwraps the result. The padding is why
you see `replace(regex_not_newline_characters, ' ')` sprinkled through these
files.

```mermaid
graph LR
    A["real source<br/>...as { y = z }..."] --> B["pad prefix with spaces<br/>+ wrap: ( { y = z } = 1 )"]
    B --> C["parse_expression_at(padded, offset)"]
    C --> D["AssignmentExpression"]
    D --> E["take .left<br/>= the Pattern"]
    E --> F["start/end already<br/>match real source"]
```

---

## 4. The Five Readers

### 4.1 Expression & pattern readers → [compiler_parse_readers_expression](compiler_parse_readers_expression.md)

Files: `read/expression.js`, `read/context.js`

The busiest readers by far. `read_expression` runs for every `{tag}`, every
`attr={value}`, and every block head (`{#if ...}`, `{#key ...}`, `{#await ...}`).
`read_pattern` runs for the destructuring positions (`{#each x as {a, b}}`,
`{:then value}`, `{:catch err}`).

Their real complexity is not the happy path — Acorn does that — but the
after-work: rewinding over trailing comments, balancing parentheses that Acorn
excluded from the node, and the **loose mode** fallback where a failed parse
becomes an empty `Identifier` that stretches to the matching `}`.

### 4.2 Style reader → [compiler_parse_readers_style](compiler_parse_readers_style.md)

File: `read/style.js`

A complete, self-contained, hand-written CSS parser: rules, at-rules, nested
rules, declarations, and the full selector grammar (type, class, id, attribute,
pseudo-class, pseudo-element, nesting `&`, combinators, `nth-of`, percentages).
It builds the CSS AST that phase 2 scopes and phase 3 rewrites — see
[compiler_css_transform](compiler_css_transform.md).

This is the only reader that does not touch Acorn at all.

### 4.3 Script reader → [compiler_parse_readers_script](compiler_parse_readers_script.md)

File: `read/script.js`

Scans to the closing `</script>`, hands the body to Acorn as a full `Program`,
and validates the tag's attributes (`module`, the legacy `context="module"`,
`lang`, `generics`). Produces the `AST.Script` node that becomes `root.js`.

### 4.4 Options reader → [compiler_parse_readers_options](compiler_parse_readers_options.md)

File: `read/options.js`

Turns the already-parsed `<svelte:options>` element into a typed
`AST.SvelteOptions` object: `runes`, `namespace`, `css`, `customElement`
(including its nested `props` / `shadow` / `extend` shape and custom-element tag
name validation), plus the legacy `immutable` / `accessors` /
`preserveWhitespace` flags.

Unlike the other four, this one runs **after** the template is fully parsed —
the `Parser` constructor pulls the `SvelteOptions` node out of the root fragment
and calls `read_options` on it. So it takes a *node*, not the parser.

---

## 5. Who Calls What

```mermaid
graph TD
    FRAG["state/fragment.js"] --> ELEM["state/element.js"]
    FRAG --> TAG["state/tag.js"]
    FRAG --> TEXT["state/text.js"]

    ELEM -->|"&lt;script&gt;"| RS["read_script"]
    ELEM -->|"&lt;style&gt;"| RST["read_style"]
    ELEM -->|"attr={expr}, directives"| RE["read_expression"]
    ELEM -->|"let:x"| RP["read_pattern"]

    TAG -->|"{#if} {#key} {#await} {@html} {@const}"| RE
    TAG -->|"{#each .. as p} {:then p} {:catch p}"| RP

    IDX["1-parse/index.js<br/>Parser constructor"] -->|"after full parse"| RO["read_options"]

    RE --> PEA["parse_expression_at"]
    RP --> PEA
    RS --> ACP["acorn.parse"]
    RE --> FMB["find_matching_bracket"]
    RP --> MB["match_bracket"]

    subgraph readers["compiler_parse_readers"]
        RE
        RP
        RS
        RST
        RO
    end

    subgraph interop["compiler_parse_js_interop"]
        PEA
        ACP
    end

    subgraph utils["compiler_parse_utils"]
        FMB
        MB
    end

    style readers fill:#e8f0fe,stroke:#4285f4
```

---

## 6. Strict Mode vs Loose Mode

The parser has a `loose` flag. The compiler sets it to `false`; the Svelte
language server sets it to `true` so it can still produce a tree for half-typed
code.

```mermaid
flowchart TD
    S["reader hits invalid syntax"] --> Q{"parser.loose?"}
    Q -->|"no &mdash; compile"| E["parser.acorn_error()<br/>throw js_parse_error<br/>with source position"]
    Q -->|"yes &mdash; editor"| B{"can we find the<br/>matching bracket?"}
    B -->|"yes"| PH["emit Identifier with name: ''<br/>jump cursor to the bracket<br/>keep parsing the rest of the file"]
    B -->|"no"| E
```

The placeholder node — an `Identifier` whose `name` is the empty string — is the
signal downstream phases use to mean *"there was an expression here, but we do
not know what it was."*

One important exception lives in `{#each}`: `read_expression` accepts a
`disallow_loose` flag. `{#each x as { y = z }}` legitimately fails as an
expression, and the `{#each}` handler *needs* that failure so it can backtrack
to the `as` keyword and re-read the tail as a pattern. Suppressing the throw
would break that recovery. See
[compiler_parse_state_machine_tag](compiler_parse_state_machine_tag.md).

---

## 7. Error and Warning Surface

The readers are one of the loudest sources of user-facing diagnostics:

| Kind | Examples |
| --- | --- |
| JS parse errors | `js_parse_error`, `expected_token`, `expected_pattern` |
| Script errors | `element_unclosed`, `script_reserved_attribute`, `script_invalid_attribute_value`, `script_invalid_context` |
| Script warnings | `script_unknown_attribute` |
| CSS errors | `css_selector_invalid`, `css_expected_identifier`, `css_empty_declaration`, `unexpected_eof` |
| Options errors | `svelte_options_unknown_attribute`, `svelte_options_invalid_customelement`, `svelte_options_invalid_tagname`, `svelte_options_reserved_tagname`, `svelte_options_deprecated_tag` |

All of them are raised through the shared `errors.js` / `warnings.js` helpers and
carry absolute source offsets, which is what lets
[compiler_core](compiler_core.md)'s `get_code_frame` print a pointer at the exact
character.

---

## 8. Documentation Map

### Sub-modules of `compiler_parse_readers`

| Document | Source files | Covers |
| --- | --- | --- |
| [compiler_parse_readers_expression](compiler_parse_readers_expression.md) | `read/expression.js`, `read/context.js` | `read_expression`, `get_loose_identifier`, `read_pattern`, `read_type_annotation` |
| [compiler_parse_readers_style](compiler_parse_readers_style.md) | `read/style.js` | `read_style`, `read_selector`, `read_at_rule`, `read_declaration` |
| [compiler_parse_readers_script](compiler_parse_readers_script.md) | `read/script.js` | `read_script` |
| [compiler_parse_readers_options](compiler_parse_readers_options.md) | `read/options.js` | `read_options` |

### Suggested reading order

1. **[compiler_parse_readers_expression](compiler_parse_readers_expression.md)** —
   establishes the cursor contract and the offset-preservation trick that the
   others reuse.
2. **[compiler_parse_readers_script](compiler_parse_readers_script.md)** — the
   simplest reader; a good place to see the contract with less noise.
3. **[compiler_parse_readers_options](compiler_parse_readers_options.md)** —
   pure validation, no cursor work.
4. **[compiler_parse_readers_style](compiler_parse_readers_style.md)** — the
   biggest, and independent of everything else.

### Neighbouring modules

| Document | Why you would go there |
| --- | --- |
| [compiler_parse](compiler_parse.md) | Parent module — the `Parser` class and phase-1 entry point |
| [compiler_parse_state_machine](compiler_parse_state_machine.md) | The caller of every reader |
| [compiler_parse_state_machine_element](compiler_parse_state_machine_element.md) | Calls `read_script`, `read_style`, `read_expression` |
| [compiler_parse_state_machine_tag](compiler_parse_state_machine_tag.md) | Calls `read_expression` / `read_pattern` for blocks; owns the `{#each}` backtracking |
| [compiler_parse_js_interop](compiler_parse_js_interop.md) | The Acorn wrapper the JS readers delegate to |
| [compiler_parse_utils](compiler_parse_utils.md) | `find_matching_bracket`, `match_bracket`, entity decoding |
| [compiler_ast_types](compiler_ast_types.md) | Shape of every node the readers build |
| [compiler_css_transform](compiler_css_transform.md) | What later happens to the CSS AST |
| [compiler_core](compiler_core.md) | Diagnostic rendering (`get_code_frame`) |
