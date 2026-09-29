# Code conventions and the review bar

> **Note.** This document was written with AI assistance and is not part of the AWS documentation for RES. Treat it as directional: verify anything you depend on against the source tree and your own deployment.

What a change to RES is expected to look like, and what a reviewer checks before approving it. The
conventions here were enforced by review rather than by tooling, so `tox -e lint` does not check them.

**Markers.** These are the conventions the RES team applied in review rather than rules derived from the
code. Where the code disagrees with a rule stated here, the code is usually older than the rule. Items
marked `[from source]` were read from the 2026.09 tree and not exercised on a running deployment.
`[verified]`, used in `docs/develop/architecture.md`, means observed on a running deployment.

## Scope

- §1 the three layers, and what may live in each
- §2 the API contract is the schema, not the code
- §3 legacy code, and which parts of it are still allowed
- §4 errors and logging
- §5 tests, including what makes a change unmergeable
- §6 duplication, magic values, function size, nesting, imports and shared state
- §7 reviewing for security
- §8 how a change is reviewed and approved
- §9 a self-review checklist

What a deployment consists of and how the layers map onto it is `docs/develop/architecture.md`.
This document is the rules; that one is the reasoning. Building and deploying any of this is
`docs/develop/deploying-from-source.md`.

---

## 1. The three layers

`[from source]` Three directories carry three responsibilities. The boundaries between them were the most
frequently enforced rule in review:

| Layer | Directory | Responsibility |
|---|---|---|
| API | `source/idea/backend/` | Authorize the caller, validate input, serialize, call the library, build the response |
| Service | `source/idea/library/` | All business logic. Shared by Lambda functions, infrastructure hosts and container tasks on Amazon ECS |
| Data model | `source/idea/data-model/` | Models and serializers. Generated, not written |

The rules that follow from this:

- **No business logic in the API layer.** Branching on a domain concept in a controller means the
  decision belongs in the library.
- **No API-style input validation in the library.** The library assumes its inputs were validated at the
  API boundary. Defensive precondition checks are fine; format, type and required-field checks are not.
- **The library takes native Python dictionaries that follow the DynamoDB record schema**, not data model
  objects. Passing a model object into the library is a layer violation even though it works.
- **Each serializer handles its own type.** A parent serializer that also serializes a nested type is
  duplication that will eventually diverge.
- **Shared helpers, utilities, constants and exceptions live in the library.** Before writing a helper,
  look for it: `source/idea/library/src/res/utils/` already holds table access and string handling.
- **HTTP status discipline.** An authorization or validation failure is a 4xx. A RES defect is a 5xx.
  Reviewers checked every error path for this, because the wrong class turns a customer's mistake into
  what looks like an outage.

## 2. The API contract is the schema, not the code

`[from source]` Smithy models under `source/res/api/spec/smithy/` define the API. Gradle builds them and
**generates** the OpenAPI specification, the data models and the serializers **from them**.

- **Never hand-edit generated files.** When a model changes, regenerate and replace the file or
  directory wholesale rather than copying a diff into the old version.
- **Constraints belong in the model**, not in code: `@required`, `@length`, `@range`, `@pattern`.
- **Do not re-validate what the framework already validates.** Required fields and types are enforced
  from the specification at request time. The same check in a controller is duplication that will
  eventually disagree with the model.
- **Enums that appear in a request or response are defined in Smithy**, not only as Python enums.

Custom validation that the schema can't express, for example "does this project exist", is the API
layer's job and belongs in the controller.

## 3. Legacy code, and which parts are still allowed

`[from source]` RES descends from two earlier projects, IDEA and SOCA, and their names and libraries are
still in the tree: `source/idea/idea-data-model/` and `source/idea/idea-sdk/` alongside the current
`source/idea/data-model/` and `source/idea/library/`. Which implementation applies depends on the component:

- **The current library and data model are for all new code.**
- **The IDEA data model and the IDEA SDK are permitted only in the legacy components**, meaning the
  cluster manager and, in releases that still have it, the virtual desktop controller.
- **If new code needs something from the IDEA SDK, move it into the library** and bring it up to current
  standards rather than importing it where it sits.
- **Do not use `Idea` or `Soca` in new identifiers.** Use `Res`.
- **Do not use the legacy `SocaException`.** See §4.

## 4. Errors and logging

- **Never write a bare `except:`.** It catches `SystemExit` and `KeyboardInterrupt`.
  `except Exception as e:` is the floor, and a specific type is better:
  `botocore.exceptions.ClientError`, `KeyError`.
- **Prefer the standard library's exception types in the library layer.** Define a custom exception only
  when something elsewhere catches that type specifically.
- **Do not catch and continue on a critical operation.** Secret retrieval, authorization and resource
  creation either succeed or fail. Let the failure surface rather than substituting a default and
  carrying on. For secrets, see §7.
- **Use `logger`, never `print()`.**
- **Log an exception at `ERROR` or `WARNING`.** Logging a failure at `INFO` is how a failure becomes
  invisible in a dashboard.
- **Log enough to diagnose**: identifiers, the operation, the parameters that mattered. Log nothing
  secret or personal.
- **Proofread log messages.** They end up in production dashboards and outlive the change.

## 5. Tests

**Missing tests are blocking, not a nit.**

**Unit tests are required for new code**, in every component: infrastructure, Lambda functions, the
infrastructure host applications and the library. Cover the happy path and the error paths, and the edges
that actually break: empty input, `None`, maximum lengths, boundaries.

**Per API, integration tests cover four cases**, and each one asserts the response body as well as the
status:

1. golden path as an administrator
2. golden path as a non-administrator
3. a client error, meaning authorization failure or invalid input, returning the right 4xx
4. that a 4xx is a 4xx and not a 5xx, which is the check that catches a mislabeled error class

**Every bug fix gets a regression test** covering the reported failure.

Test hygiene that reviewers enforced:

- Clean up whatever a test creates.
- Keep account identifiers and region-specific ARNs out of test data.
- Mock external services, not your own logic.
- Do not add a test-only hook to production code to make something testable.
- Name a test for what it tests.

`[from source]` One caution about the shipped suite: `source/tests/unit/idea-administrator/` contains a
single placeholder test, so a change there needs tests written alongside it.

## 6. Duplication, magic values, function size, nesting, imports and shared state

- **Do not copy and paste blocks.** The recurring instance is one block per enumeration member, seven for
  the days of the week, where a loop with `getattr` and `setattr` does the same work.
- **Do not hardcode strings or numbers.** Name them. Where a number encodes a reason, say what the reason
  is, and make timeouts, retry counts and thresholds configurable or documented.
- **Make each function do one thing.** Anything past about fifty lines gets flagged.
- **Keep nesting at three levels or fewer.** Use early returns and extraction, not deeper indentation.
- **Put imports at the top of the file**, unless a lazy import is deliberate and says so.
- **Do not write a wrapper class that carries no state.** A class of `@staticmethod` methods is a module
  of functions.
- **Synchronize module-level mutable state.** A dictionary used as a cache is shared across threads on
  the infrastructure hosts. Use a lock or `functools.lru_cache`. Concurrency was consciously deferred in
  this codebase, so new code should not add to the debt.
- **Handle both platforms or say why not.** If a change affects Linux behavior, ask what it does on
  Windows. Build paths with `pathlib` or `os.path`, never by concatenating separators.

## 7. Reviewing for security

Treat security review as a separate pass with its own checklist, run first rather than last: a
correctness problem costs a revision, a security problem costs an incident.

This section is **method only**. It says where to look and what to ask. It contains no assessment of
whether any particular part of RES is or has been vulnerable, and it's not a threat model: assess
exploitability against your own deployment and environment.

### 7.1 The checklist applied to every change

**Input validation and injection**

- Validate every user-controllable value before use, against an allowed set rather than by filtering for
  known-bad characters.
- Do not interpolate a string into a shell command. Use `shlex.quote()` or an argument list.
- Do not interpolate a string into a query.
- Do not render raw user input into markup.
- Check resource identifiers arriving from a caller, meaning subnet identifiers, instance types and ARNs,
  against what is allowed rather than trusting them.

**Secrets**

- Do not hardcode a secret, token, password or default credential.
- **Give a secret no fallback value.** If retrieval fails, the operation fails.
- Do not construct a token with a predictable or default signing key.
- Log a retrieval failure at `ERROR`.

**Authorization**

- Check in every operation that the caller is authorized for **the specific resource**, not merely
  authenticated.
- Enforce an administrator-only operation explicitly.
- Do not leave a test or debug switch reachable by a caller, including an environment variable whose
  default relaxes validation.

### 7.2 The periodic tree-wide sweep: constructs to search for, and the questions to ask

A periodic self-review of the whole tree, rather than of one change, was run
against a list of construct classes. The list below is that method: the search is cheap, and the
judgment is in the questions rather than in the match.

| What to search for | Why this class matters | What to ask about each hit |
|---|---|---|
| A check followed by a separate operation on the same path: `islink`, `isfile` or a permission test, then `open`, `chown`, `rmtree`, `remove`, `copy` | Anything between the check and the use can change what the path points at | Is the check atomic with the operation, or is there a gap? What privilege does the operation run with? |
| `subprocess`, `os.system`, `os.popen`, `shell=True`, and anything that sends a command to an instance for execution | These are the sinks where an unvalidated string becomes code | Where did every interpolated value come from, and is it validated at the boundary? What privilege does the command run as, and on how many hosts? |
| User input written into a file that is later read by something that acts on it | A file is an indirect command sink and is easy to miss when reviewing the write | Same questions as a direct command sink, plus: who reads this file, and as whom? |
| Username and identifier normalization before a lookup: splitting, truncating, lowercasing | A value that is normalized before an authorization decision may not be the value that was authenticated | Can two distinct principals normalize to the same string? Is the identity used for the decision the one the authenticator issued? |
| Endpoints that return configuration or settings | A settings response is a convenient inventory of an environment | Is the response filtered by the caller's role? Does it contain directory bind identities, endpoints, or resource metadata a caller has no need for? |
| Exception text returned to a caller, `str(e)` or a traceback in a response body | Diagnostics are useful to an attacker in the same way they are useful to you | Does this leak a path, a query, or an internal identifier? |
| Path canonicalization, `realpath`, `abspath`, or a prefix comparison used as a boundary | A boundary check is only as good as its atomicity with the access | Is the canonicalized path the one that is then opened? Does the operation follow symbolic links? |
| Archive creation and extraction, `zipfile`, `tarfile`, `make_archive` | Archives carry links and paths that escape the directory they appear to be in | What happens to a link or an absolute path inside the archive? |
| A numeric limit enforced by counting, comparing, then creating | Concurrent callers can all pass the comparison before any of them commits | Is the check and the create one atomic operation, for example a conditional write? If not, how many concurrent requests defeat it? |
| Absence of `ConditionExpression` or equivalent where a limit or uniqueness matters | The absence is the finding | As above |

**Two disciplines that keep this useful.** Follow the whole call chain before flagging anything, because
validation frequently lives at the boundary rather than at the sink, and a report that ignores it is
noise. And judge exploitability rather than pattern-matching: a construct with no reachable caller is
worth noting, not escalating.

### 7.3 Rating what you find

The rubric in use, and the discipline that goes with it:

| Rating | Means |
|---|---|
| CRITICAL | Remote code execution, escalation to administrator or root, or access to another user's data |
| HIGH | Disclosure of credentials or secrets, or arbitrary read, write or deletion of files |
| MEDIUM | A limit bypass, disclosure of non-sensitive metadata, or a denial-of-service opening |
| LOW | Theoretical, or with preconditions an attacker is unlikely to arrange |

**Do not rate anything CRITICAL without a concrete path from an attacker's position to the impact.** A
construct that could be serious if several unproven things were true is HIGH at most.

Where to report something you find in RES rather than in your own fork: `SECURITY.md`.

## 8. How a change is reviewed and approved

**Keep a change to roughly 500 lines of source and 500 lines of tests.** Not a rule about correctness, a
rule about review quality: past that size, review gets slower and worse at the same time. A change that
exceeds it should be split, and the reviewer should say how to split it rather than only that it's too
big.

**One change, one subject.** A feature plus an unrelated cleanup is two pull requests.

**Findings carry a severity**, and the severity decides what happens:

| Severity | Meaning | Effect |
|---|---|---|
| HIGH | Correctness, security, or a layer violation that will have to be undone | Blocks the merge |
| MEDIUM | Should be fixed, but need not be fixed here | Blocks the merge unless it is fixed or there is a tracked follow-up item |
| LOW | Style and preference | Does not block |

**Approve when there are no HIGH findings.** Every MEDIUM finding must be either fixed in the change or
tracked somewhere a reader can find it. Request changes on any HIGH finding, or on a MEDIUM finding with
neither a fix nor a tracked item.

Security findings run on their own track: §7 is the checklist and the rating scale, and a security
finding was reviewed first rather than in severity order with the rest.

**Comment on the line, not on the change.** A reviewer's finding belongs inline where the code is. Write
it in a form the author can act on without reading the rest of the review: what is wrong, why it matters,
and a suggested fix. Add one summary comment with the counts, the follow-up items, what was done well,
and the recommendation.

**Tone conventions that were in active use**: `Nit:` prefixes a style suggestion the author may ignore;
`Curious:` prefixes a question rather than an accusation. Both exist so that a large review does not read
as an attack. When flagging a problem in ported code, say that you know it is ported, and still flag it.

This document states no approver count, because that is a decision for whoever maintains the fork.

## 9. Self-review checklist

The findings most worth checking for before asking anyone else to read a change:

1. **Missing tests**, especially a bug fix with no regression test.
2. **Layer boundary violations**: business logic in a controller, API validation in the library, or a
   hand-edited generated file.
3. **Bare or overly broad `except:`**, which hides the defect you're about to ship.
4. **Validation written in code that the schema already enforces.**
5. **Wrong error class**, a 5xx for what is a client mistake or the reverse.
6. **Hardcoded values and magic numbers.**
7. **Duplication**, either copy-paste per enumeration member or a new helper that reimplements one in
   the library.
8. **Legacy usage in new code**: `Idea` or `Soca` naming, or importing the IDEA SDK or data model.
9. **Missing input sanitization** (§7), particularly anything that reaches a shell command or names an
   AWS resource.
10. **A secret with a fallback default.**
11. **`print()` instead of `logger`, or an exception logged at `INFO`.**
12. **Data model objects passed into the library** instead of dictionaries.
13. **API tests missing the administrator or the non-administrator path.**
