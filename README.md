# sonnet-py
Rhea replacement, written in Python.

## Initialising Development Environment
On Windows, run ``init_env.bat`` which is located in ``build_tools\win`` and follow the instructions appropriately.

Before pushing, remember to execute ``prepare_push.bat`` - this may not be required in the future but is a good thing to use in order to sanitize a build if you aren't using Git as your source control system.

## Roadmap

- [x] Fix shoddy command processing code.
- [ ] Migrate all commands from Rhea to Sonnet codebase.
- [ ] Ensure that data migration between Rhea and Sonnet is seamless (same DB types, accessing in same way etc.)
- [ ] Stress-test and gather bugs, fix problems.
- [ ] Work on branding, promo material etc.
- [ ] Release to public.
