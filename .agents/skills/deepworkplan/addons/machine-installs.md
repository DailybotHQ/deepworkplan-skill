# Addons — machine-level installs and upgrades (verified)

Read from `../onboard/all-addons.md` §4, or from an addon's own install step.
These commands change the developer's machine, not the repository: show
them, and run them only when the developer accepts, in an interactive
session. Each tag below is the pack's pin for that addon (its `addon.json`
`product.tag`, printed by `../shared/addon_sync.py plan`).

**Kits.** Both installers upgrade in place, so install and upgrade are the
same sequence at the pin, with three gates before the installer runs: the
tag checked, the downloaded `SHA256SUMS` checked against the digest pinned
here, and the tree checked against `SHA256SUMS` with at least one file
actually verified (`--ignore-missing` alone would pass with none).

coding-agents-kit (`agentkit`):

```bash
git clone --branch v0.5.0 --depth 1 https://github.com/DailybotHQ/coding-agents-kit cak
git -C cak describe --tags --exact-match            # must print v0.5.0
curl -fsSL https://github.com/DailybotHQ/coding-agents-kit/releases/download/v0.5.0/SHA256SUMS -o cak.SHA256SUMS
echo "a90f45e44085370694a954a3578d037d0637d0eb4ec2f1b846a8d29556b1ec27  cak.SHA256SUMS" | shasum -a 256 -c   # the pinned digest
(cd cak && shasum -a 256 -c --ignore-missing ../cak.SHA256SUMS)       # must exit 0
(cd cak && shasum -a 256 -c --ignore-missing ../cak.SHA256SUMS | grep -c ': OK$')   # must print a number above 0
./cak/install.sh
```

devcontainer-kit (`devcontainer`):

```bash
git clone --branch v0.3.0 --depth 1 https://github.com/DailybotHQ/devcontainer-kit dck
git -C dck describe --tags --exact-match            # must print v0.3.0
curl -fsSL https://github.com/DailybotHQ/devcontainer-kit/releases/download/v0.3.0/SHA256SUMS -o dck.SHA256SUMS
echo "02d4de086eeb010b42458dd131b690df36638b361033e5df6aa3d5ceba4a7eea  dck.SHA256SUMS" | shasum -a 256 -c   # the pinned digest
(cd dck && shasum -a 256 -c --ignore-missing ../dck.SHA256SUMS)       # must exit 0
(cd dck && shasum -a 256 -c --ignore-missing ../dck.SHA256SUMS | grep -c ': OK$')   # must print a number above 0
./dck/install.sh
```

Re-detect afterwards (`ak doctor --json`, `dck doctor --json`); the
interface must match the descriptor. dck additionally installs the
repository-local `dck-dockerfile` skill at the same tag
(`devcontainer/SKILL.md`, Step 2).

**herdr-peers** (host): the pinned skill installs in
`herdr/install.md`; `dck setup` also installs a verified
herdr-peers on the host. Verify with `herdr-peers --version`
(`(protocol 1)`).

**DeepWorkPlan Vim:** the product's own checksum-verified installer under
its consent gate (`vim/SKILL.md`); an existing Neovim config is
never overwritten without explicit consent.

A failed tag check or a checksum mismatch stops the install: report it,
never run the installer anyway. Never pipe a download into a shell, never
install a coding-agent CLI the developer did not choose, and never set an
autonomy flag.
