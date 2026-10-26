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
