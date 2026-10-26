# Who Owns the Quota

*Why an API call can be enabled in one project and still be refused by another — and what a
free-tier sweep actually costs.*

## The symptom

Enable a Google API in your `gcloud` default project. Call it with a valid OAuth token. The
answer comes back:

```
403 PERMISSION_DENIED
SERVICE_DISABLED
<API name> has not been used in project 000000000000 before or it is disabled.
```

The project number in that message is **not** the project you just enabled. That is the whole
note: read the number as an address, not as a complaint about the project you were thinking
about.

## Two credentials, two owners

| Credential | Enablement is checked against | Override |
| --- | --- | --- |
| API key | the project the **key** belongs to | none |
| OAuth access token | the project the **OAuth client** belongs to | `x-goog-user-project` header |

There is no project in the URL, which is exactly the trap. A URL like
`https://classroom.googleapis.com/v1/courses` looks project-neutral, and the project arrives
*inside* the credential. So the same request can be green with one credential and
`SERVICE_DISABLED` with another while nothing in the request changed.

The corollary is a design question, and it is cheap to ask early: when a system holds more than
one credential, **which project does each one name?** If the answer is "two different
projects", you will be enabling the same service twice, or supplying the override header, or
meeting the wall later under load.

## Three walls, checked in order, only the first reported

1. `SERVICE_DISABLED` — the API is off in the credential's project.
2. `BILLING_DISABLED` — the API is on, but this project has no open billing account and the API
   is a billed one.
3. **Key restriction** — "requests from this API are blocked": the key's `apiTargets` list does
   not include this service.

Because (1) masks (2) and (3), triage that stops at the first message misdiagnoses
systematically. Two facts that look identical from the outside — *no billing account* and *a
billing account that exists but is closed* — are not identical at all.

## Not every block is about you

The most misleading message of the day:

> This app is blocked. This app tried to access sensitive info in your Google Account.

This is **not** a policy applied to the account, and there is nothing to click in the API
dashboard to lift it. It means the **OAuth client making the request** is not permitted to ask
for those scopes — in this case the vendor's own command-line client, allowlisted for a narrow
set and refusing everything outside it. The fix is not permissions but *provenance*: run the
flow with your own installed-app client. Same scopes, same account, consent granted first try.

The generalisable reading: **"blocked" is a claim about the caller, and the caller is a
decision you can change.**

## The scope you ask for is not always the scope you get

Requesting two Classroom *coursework* read scopes returned two Classroom *student-submissions*
read scopes instead, with every other scope identical. A provider is entitled to answer with a
neighbouring granularity. Therefore:

- store what the provider actually returns, not what you requested;
- do not let a general-purpose OAuth library turn "returned ≠ requested" into a fatal error —
  one library does exactly that, and it will make you throw away a valid grant;
- verify behaviour with a call, because a scope name that *looks* like it covers a resource may
  not: `…courses.readonly` lists courses but says nothing about their announcements.

## The freebies, measured

What can be switched on and actually answered with **no billing account**, by public API name:

| API | Result |
| --- | --- |
| Blogger v3 | `200` — blogs and posts |
| Books v1 (My Library) | `200` — shelves and volumes |
| Classroom v1 | `200` — a personal account is not barred |
| YouTube Data v3 | `200` — public search |
| PageSpeed Insights v5 | `200` |
| Custom Search JSON API | `400` until a search-engine id (`cx`) exists; fine afterwards |
| Tenor | refused at **enablement**: `servicemanagement.services.bind` denied — allowlisting, not billing |
| Maps Pollen / Air Quality / Solar / Aerial View | all billed; a **closed** billing account keeps them shut |

Two quirks worth carrying forward. Books answers `503` intermittently — the same query returned
`200`, then `503` three seconds later, and a `country=` parameter made no difference either
way — so retry with backoff instead of re-reading the documentation. And a key is bound to
exactly one project, so a *second* key restricted to the free set is cheaper than widening a
key that already works elsewhere: one credential per purpose stays disposable.

## The transferable part

- **The credential names the project.** Read that number as "who is asking", never as "what is
  broken".
- **Walls mask each other.** Enumerate them before concluding, because the error you see is
  simply the first check that failed.
- **"Blocked" usually means "wrong client".** Changing the client is a legitimate fix, not a
  workaround.
- **Accept the answer you get.** Validate at the edge; do not let an SDK veto the provider.

## Cross-links

- [The Four Gates of an MCP Server](./mcp_migration_gates.md) — this is gate **G4** in detail:
  the process is fine, the config is fine, and the provider still says no.
- [The Grant I Threw Away](../self_discoveries/the_grant_i_threw_away.md) — the same scope
  substitution seen from the other side: a library rejecting a grant the provider had already
  given.
