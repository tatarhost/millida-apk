# Third-party source and license notice

This APK prototype is built from the following public source:

- Amethyst-Android: https://github.com/AngelAuraMC/Amethyst-Android
- Pinned source commit: 28d6e12d68121b7dd75f2e841058a6b7cdfe4a29
- License in that revision: GNU LGPL v3 (see upstream LICENSE).

The upstream project includes additional third-party components with their own license terms; see upstream README.md, THIRD-PARTY.md, and bundled license files. No Amethyst signing key is reused: the workflow creates a temporary TatarHost test key.

This prototype does not contain the Millida PC source or claim to be a complete Android port of it. It uses Amethyst as an Android Java runtime/launcher foundation while the PC project's separate features are still to be ported. The identity overlay in scripts/prepare-upstream.py changes the Android package ID, visible app label and launcher icon.
