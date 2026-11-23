# Knowledge Graph

Structured learnings, concepts, and cross-linked notes — the connective tissue
of the garden.

## Notes

- [Native Binaries Shipped Through npm](./native_npm_binaries.md) — how a JavaScript
  launcher finds a compiled payload, why an unusual platform name breaks it twice, and
  how to extend it without building an emulator that was never needed.
- [PairIP: The Gate Is One Attribute](./pairip_one_attribute.md) — how Play's licensing
  wrapper attaches to an APK, why repointing one manifest attribute disarms it, and the
  AXML/ZIP/signature mechanics that have to be right for the result to install.
- [The Four Gates of an MCP Server](./mcp_migration_gates.md) — why connecting a tool server
  fails in four different ways that all look alike: the code runs, the client knows about it,
  the process can see what it needs, the provider accepts who is calling — and the recipe
  that tests them in the right order.
- [Who Owns the Quota](./who_owns_the_quota.md) — why an API can be enabled in one project and
  still be refused by another: the credential names the project, three walls mask each other,
  and "this app is blocked" is a fact about the caller, not the account.
- [The Alarm That Was Silently Dropped](./vendor_alarm_firewall.md) — a vendor ROM that
  filters `AlarmManager` against a static allowlist, why the app still logs success, why the
  Doze whitelist and the vendor's own "app freeze" UI are decoys, and the broadcast receiver
  that un-restricts a package.
- [One Stray Config File](./one_stray_config_file.md) — a project-scope config silently shadowed
  the global one, so a working server looked broken: name the binary rather than the package,
  read an empty log as a fact about the parent, and audit "which config won?" at step zero.
- [A Passport Is Not a Deed](./provenance_is_not_permission.md) — a disabled Play Store made
  five paid-for-nothing apps declare themselves stolen: why provenance, integrity and
  entitlement are three questions answered as one, why the guard was only ever a name in the
  manifest, and what the phone's memory of an uninstalled app says about identity.
- [The Kill That Named Itself](./the_kill_that_named_itself.md) — a vendor ROM killed one app
  roughly hourly for three days and reported a reason that was a lie: why the log is a
  five-minute memory, why the exit store outlives it, what `o-kill:6` is a receipt for, and
  the single GUI toggle that ended it — verified with a 3.9 GB load experiment rather than
  with silence.
- [The Prompt That Kept Its Receipts](./the_prompt_that_kept_its_receipts.md) — a harness
  announced "Instructions updated: core/codemode, core/mcp-guidance" and nothing had been
  edited: how a system prompt becomes content-addressed layers in three SQLite tables, and
  why "updated" can mean the world changed rather than the human did.
- [The Name That Was Not a Promise](./the_name_that_was_not_a_promise.md) — a frozen
  `whisper-cli` refused to load after ffmpeg was upgraded under it, and "the libraries are
  newer, that shouldn't matter" turned out to be three different promises: a dropped name, a
  changed soname, and a symbol renamed while the soname stayed the same — why the last one
  is unfixable by any link trick, and the reversible patches that bridged it anyway.
