# Kimai Command Line Interface (CLI)

:fire: A command line interface for the Kimai time tracking software.

## Installation

You can install `kimai-cli` through Homebrew.

```bash
brew tap ksassnowski/kimai-cli
brew install kimai-cli
```

You can now use the `kimai` command in your shell. Before first use you need to run

```bash
kimai configure
```

This will prompot you for your kimai URL (e.g. `https://kimai.your-site.com`) and your login credentials.
These credentials will only be used to retrieve your api key from the Kimai backend. They will not be stored
anywhere.

## Updating

You can update the cli like any other brew tap:

```bash
brew update
brew upgrade kimai-cli
```

## Autocompletion

For `zsh`, put this into your `.zshrc`

```bash
autoload bashcompinit
bashcompinit
eval "$(_KIMAI_COMPLETE=source kimai)"
```

If you're using `bash` you can leave out the first two lines and simply put this into your `.bashrc`

```bash
eval "$(_KIMAI_COMPLETE=source kimai)"
```
