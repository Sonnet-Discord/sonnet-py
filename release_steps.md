# Procedure for releasing a new version of Sonnet
This is an internally used checklist for releasing a new sonnet version, it is available publicly because there is no reason to hide it, and it makes it convenient for maintainers to find  
1. Run `codespell`
1. Open new version PR (`dev-unstable` -> `main`)
1. Pass code review on new version PR
1. Remove `-dev` tags from sonnet core modules (cmds and dlibs)
1. Ensure all updated cmds and dlibs receive new version
1. Decide on name for new version
1. Locally create toml changelog in sonnet-website repository by referencing new version PR diff and commit history
1. Locally update command reference on website using `cmds_to_html.py`
1. Locally update latest version download link on website
1. Export changelog without name to draft gh release and PR, using a new git tag for the new version
1. Merge PR
1. Immediately publish website changes and publish github release with new version name
1. Post to sonnet support server that a new version was released
1. Update instances we manage, mainly Summit and Remi
1. If any bugs occur, create new patch release and thoroughly test before publishing again

