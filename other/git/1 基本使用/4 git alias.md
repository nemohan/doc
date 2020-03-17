# Git Alias

This section will focus on Git aliases. To better understand the value of Git aliases we must first discuss what an alias is. The term alias is synonymous with a shortcut. Alias creation is a common pattern found in other popular utilities like `bash` shell. Aliases are used to create shorter commands that map to longer commands. Aliases enable more efficient workflows by requiring fewer keystrokes to execute a command. For a brief example, consider the `git checkout` command. The checkout command is a frequently used git command, which adds up in cumulative keystrokes over time. An alias can be created that maps `git co` to `git checkout`, which saves precious human fingertip power by allowing the shorter keystroke form: `git co` to be typed instead.

## Git Alias Overview

It is important to note that there is no direct `git alias` command. Aliases are created through the use of the `git config` command and the Git configuration files. As with other configuration values, aliases can be created in a local or global scope.

To better understand Git aliases let us create some examples.

```
$ git config --global alias.co checkout
$ git config --global alias.br branch
$ git config --global alias.ci commit
$ git config --global alias.st status
```

The previous code example creates globally stored shortcuts for common git commands. Creating the aliases will not modify the source commands. So `git checkout` will still be available even though we now have the `git co` alias. These aliases were created with the `--global` flag which means they will be stored in Git's global operating system level configuration file. On linux systems, the global config file is located in the User home directory at `/.gitconfig`.

```
 [alias]
 co = checkout
 br = branch
 ci = commit
 st = status
```

This demonstrates that the aliases are now equivalent to the source commands.

## Usage

Git aliasing is enabled through the use of `git config`, For command-line option and usage examples please review the `git config `documentation.

## Examples

### Using aliases to create new Git commands

A common Git pattern is to remove recently added files from the staging area. This is achieved by leveraging options to the `git reset` command. A new alias can be created to encapsulate this behavior and create a new alias-command-keyword which is easy to remember:

```
git config --global alias.unstage 'reset HEAD --'
```

The preceding code example creates a new alias `unstage`. This now enables the invocation of `git unstage. git unstage` which will perform a reset on the staging area. This makes the following two commands equivalent.

```
git unstage fileA
$ git reset HEAD -- fileA
```

## Discussion

### How do I create Git Aliases?

Aliases can be created through two primary methods:

#### Directly editing Git config files

The global or local config files can be manually edited and saved to create aliases. The global config file lives at `$HOME/.gitconfig` file path. The local path lives within an active git repository at `/.git/config`

The config files will respect an `[alias]` section that looks like:

```
[alias]
	co = checkout
```

This means that `co` is a shortcut for `checkout`

#### Using the git config to create aliases

As previously demonstrated the `git config` command is a convenient utility to quickly create aliases. The `git config` command is actually a helper utility for writing to the global and local Git config files.

```
git config --global alias.co checkout
```

Invoking this command will update the underlying global config file just as it had been edited in our previous example.

## Git Alias Summary

Git aliases are a powerful workflow tool that create shortcuts to frequently used Git commands. Using Git aliases will make you a faster and more efficient developer. Aliases can be used to wrap a sequence of Git commands into new faux Git command. Git aliases are created through the use of the git config command which essentially modifies local or global Git config files. Learn more on the `git config` page.