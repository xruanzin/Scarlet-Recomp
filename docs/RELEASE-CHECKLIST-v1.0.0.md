# v1.0.0 release gate — Scarlet-Recomp

This is a release **preparation** checklist, not proof that tests passed.

- [ ] Decide final public release presentation, screenshots, language, asset name and pre-release/stable status with repository owner.
- [ ] Confirm which functional commit is being shipped; **do not merge portrait debug/fallback branches** into v1.0.0.
- [ ] Confirm `README.md`, `README.pt-BR.md` and launcher identify Scarlet, not Z-A.
- [ ] Verify clean Windows 11 build of `scarlet.exe`, `ScarletLauncher.exe`, `scarletimport.exe` with permitted runtime dependencies.
- [ ] Verify launcher starts without undocumented environment variables or local hardcoded paths.
- [ ] Verify JOGAR starts Scarlet 4.0.0 with TLS/bootstrap allocation enabled by default, WITHOUT the old experimental checkbox or manual SCARLET_EARLY_TLS_PROBE / SCARLET_BOOTSTRAP_ALLOCATOR flags; also test direct scarlet.exe --play and startup with a stale saved launcher config.
- [ ] Check that the limited early-allocation shim does not break subsequent heap allocation/free behavior after SDK initialization; prevent unsupported reinit ordering (SCARLET_MAIN_INIT_FIRST stays off).
- [ ] Verify fresh machine workflow for users to import their own Scarlet base/update 4.0.0 and legally generate their own AOT game library; do not imply the importer generates it unless confirmed.
- [ ] Verify executable icon and launcher art are licensed for public distribution.
- [ ] Verify 30 FPS gameplay/menu/name-entry and save restart; test optional FPS modes separately.
- [ ] Confirm known black enrollment photo and any remaining rendering defects are listed accurately.
- [ ] Verify package contains **no** keys, tickets, NSP/XCI, extracted game files, saves, caches, guest-derived AOT DLL, local logs, machine identifiers or credentials.
- [ ] Review MIT/third-party license notices and include redistribution notices for every packaged dependency.
- [ ] Produce SHA-256 checksums for approved downloadable assets.
- [ ] Run available synthetic preflight CI; do not treat synthetic results as game-playability validation.
- [ ] Review selected branch and tag `v1.0.0` only after approval; attach assets only after package verification.
- [ ] Update default branch / GitHub homepage only after release-branch review (current default: `pokemon-za`).
- [ ] Publish GitHub Release only after explicit approval.
