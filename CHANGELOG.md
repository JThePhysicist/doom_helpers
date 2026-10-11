# Changelog

## Unreleased

- Reject malformed WAD headers, directory entries, patch posts, and manifests; bound resource use.
- Preserve unsigned map references and provide map-scoped editing and validation.
- Keep new sprites inside valid marker ranges; make duplicate selection explicit.
- Preserve editing allocations independently of changing crop rectangles.
- Stage output writes, recover from ordinary multi-file failures, and require explicit CLI overwrite.
- Install atlas extraction, realignment, rebuilding, and HTML preview commands.
- Select PLAYPAL palettes and optionally retain original palette indices.
- Add explicit vanilla and source-port tall-patch profiles.
- Add indexed read-only WAD access and repeatable memory measurements.
- Add a universal development lock, supported-Python CI, coverage, and isolated wheel smoke tests.
- Add optional generated-art engine smoke tooling, architecture documentation, and a user guide.

## 0.1.0

Initial Python library, inspection CLI, and repository atlas scripts. No released tag or package-registry publication is established by this changelog.
