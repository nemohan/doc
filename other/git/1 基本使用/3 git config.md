# git config

In this document, we'll take an in-depth look at the `git config` command. We briefly discussed `git config` usage on our [Setting up a Repository](https://www.atlassian.com/git/tutorials/setting-up-a-repository) page. The `git config` command is a convenience function that is used to set Git configuration values on a global or local project level. These configuration levels correspond to `.gitconfig` text files. Executing `git config` will modify a configuration text file. We'll be covering common configuration settings like email, username, and editor. We'll discuss Git aliases, which allow you to create shortcuts for frequently used Git operations. Becoming familiar with `git config` and the various Git configuration settings will help you create a powerful, customized Git workflow.

## Usage

The most basic use case for `git config` is to invoke it with a configuration name, which will display the set value at that name. Configuration names are dot delimited strings composed of a 'section' and a 'key' based on their hierarchy. For example: `user.email`

```
git config user.email
```

In this example, email is a child property of the user configuration block. This will return the configured email address, if any, that Git will associate with locally created commits.

### <font color="red">git config levels and files</font>

Before we further discuss `git config` usage, let's take a moment to cover configuration levels. The `git config` command can accept arguments to specify which configuration level to operate on. The following configuration levels are available:

- local

By default, `git config` will write to a local level if no configuration option is passed. Local level configuration is applied to the context repository `git config` gets invoked in. Local configuration values are stored in a file that can be found in the repo's .git directory: `.git/config`


-  global

Global level configuration is user-specific, meaning it is applied to an operating system user. Global configuration values are stored in a file that is located in a user's home directory. `~ /.gitconfig` on unix systems and `C:\Users\<username>\.gitconfig` on windows


-  system

System-level configuration is applied across an entire machine. This covers all users on an operating system and all repos. The system level configuration file lives in a `gitconfig` file off the system root path. `$(prefix)/etc/gitconfig` on unix systems. On windows this file can be found at `C:\Documents and Settings\All Users\Application Data\Git\config` on Windows XP, and in `C:\ProgramData\Git\config` on Windows Vista and newer.

<font color="red">Thus the order of priority for configuration levels is: local, global, system. This means when looking for a configuration value, Git will start at the local level and bubble up to the system level.</font>


### Writing a value

Expanding on what we already know about `git config`, let's look at an example in which we write a value:

```
git config --global user.email "your_email@example.com"
```

This example writes the value `your_email@example.com` to the configuration name `user.email`. It uses the `--global` flag so this value is set for the current operating system user.

## git config editor - core.editor

Many Git commands will launch a text editor to prompt for further input. One of the most common use cases for `git config` is configuring which editor Git should use. Listed below is a table of popular editors and matching `git config` commands:

| Editor                             | config command                                               |
| ---------------------------------- | ------------------------------------------------------------ |
| Atom                               | `~ git config --global core.editor "atom --wait"~`           |
| emacs                              | `~ git config --global core.editor "emacs"~`                 |
| nano                               | `~ git config --global core.editor "nano -w"~`               |
| vim                                | `~ git config --global core.editor "vim"~`                   |
| Sublime Text (Mac)                 | `~ git config --global core.editor "subl -n -w"~`            |
| Sublime Text (Win, 32-bit install) | `~ git config --global core.editor "'c:/program files (x86)/sublime text 3/sublimetext.exe' -w"~` |
| Sublime Text (Win, 64-bit install) | `~ git config --global core.editor "'c:/program files/sublime text 3/sublimetext.exe' -w"~` |
| Textmate                           | `~ git config --global core.editor "mate -w"~`               |

 

## Merge tools

In the event of a merge conflict, Git will launch a "merge tool." By default, Git uses an internal implementation of the common Unix diff program. The internal Git diff is a minimal merge conflict viewer. There are many external third party merge conflict resolutions that can be used instead. For an overview of various merge tools and configuration, see our guide on [tips and tools to resolve conflits with Git](https://developer.atlassian.com/blog/2015/12/tips-tools-to-solve-git-conflicts/). 

```
git config --global merge.tool kdiff3
```

## Colored outputs

Git supports colored terminal output which helps with rapidly reading Git output. You can customize your Git output to use a personalized color theme. The `git config` command is used to set these color values.

### `color.ui`

This is the master variable for Git colors. Setting it to false will disable all Git's colored terminal output.


```
$ git config --global color.ui false
```

By default, `color.ui` is set to auto which will apply colors to the immediate terminal output stream. The auto setting will omit color code output if the output stream is redirected to a file or piped to another process.

You can set the `color.ui` value to always which will also apply color code output when redirecting the output stream to files or pipes. This can unintentionally cause problems since the receiving pipe may not be expecting color-coded input.

### Git color values

In addition to `color.ui`, there are many other granular color settings. Like `color.ui`, these color settings can all be set to false, auto, or always. These color settings can also have a specific color value set. Some examples of supported color values are:

- normal
- black
- red
- green
- yellow
- blue
- magenta
- cyan
- white

Colors may also be specified as hexadecimal color codes like #ff0000, or ANSI 256 color values if your terminal supports it.

### Git color configuration settings

\1. `color.branch` 

- Configures the output color of the Git branch command 

\2. `color.branch.<slot`> 

- This value is also applicable to Git branch output. <

  ```
  slot
  ```

  \> is one of the following: 

  - \1. current: the current branch 
  - \2. local: a local branch 
  - \3. remote: a remote branch ref in refs/remotes 
  - \4. upstream: an upstream tracking branch 
  - \5. plain: any other ref

\3. `color.diff` 

- Applies colors to `git diff`, `git log`, and `git show` output 

\4. `color.diff`.<`slot`> 

- Configuring a <

  ```
  slot
  ```

  \> value under

   

  ```
  color.diff
  ```

   

  tells git which part of the patch to use a specific color on. 

  - \1. context: The context text of the diff. Git context is the lines of text content shown in a diff or patch that highlights changes. 
  - \2. plain: a synonym for context 
  - \3. meta: applies color to the meta information of the diff 
  - \4. frag: applies color to the "hunk header" or "function in hunk header" 
  - \5. old: applies a color to the removed lines in the diff 
  - \6. new: colors the added lines of the diff 
  - \7. commit: colors commit headers within the diff 
  - \8. whitespace: sets a color for any whitespace errors in a diff

\5. `color.decorate.<slot`> 

- Customize the color for `git log --decorate` output. The supported <`slot`> values are: `branch`, `remoteBranch`, `tag`, `stash`, or `HEAD`. They are respectively applicable to local branches, remote-tracking branches, tags, stashed changes and `HEAD`. 

\6. `color.grep`

- Applies color to the output of git grep. 

\7. `color.grep.<slot`> 

- Also applicable to git grep. The <

  ```
  slot
  ```

  \> variable specifies which part of the grep output to apply color. 

  - \1. context: non-matching text in context lines 
  - \2. filename: filename prefix 
  - \3. function: function name lines 
  - \4. linenumber: line number prefix 
  - \5. match: matching text 
  - \6. matchContext: matching text in context lines 
  - \7. matchSelected: matching text in selected lines 
  - \8. selected: non-matching text in selected lines 
  - \9. separator: separators between fields on a line (:, -, and =) and between hunks (--) 

\8. color.interactive 

- This variable applies color for interactive prompts and displays. Examples are `git add --interactive` and `git clean --interactive `

\9. color.interactive.<slot> 

- The <slot> variable can be specified to target more specific "interactive output". The available <`slot`> values are: prompt, header, help, error; and each act on the corresponding interactive output. 

\10. `color.pager`

- Enables or disables colored output when the pager is in use 

\11. `color.showBranch `

- Enables or disables color output for the git show branch command 

```
12. color.status 
```

- A boolean value that enables or disables color output for Git status 

```
13. color.status.<slot>
```

Used to specify custom color for specified git status elements. <`slot`> supports the following values:

- \1. header

  - Targets the header text of the status area

- \2. added or updated

  - Both target files which are added but not committed

- ```
  3. changed
  ```

  - Targets files that are modified but not added to the git index

- \4. untracked

  - Targets files which are not tracked by Git

- \5. branch

  - Applies color to the current branch

- \6. nobranch

  - The color the "no branch" warning is shown in

- \7. unmerged

  - Colors files which have unmerged changes

  ```
  
  ```

## Aliases

You may be familiar with the concept of aliases from your operating system command-line; if not, they're custom shortcuts that define which command will expand to longer or combined commands. Aliases save you the time and energy cost of typing frequently used commands. Git provides its own alias system. A common use case for Git aliases is shortening the commit command. Git aliases are stored in Git configuration files. This means you can use the `git config` command to configure aliases.

```
git config --global alias.ci commit
```

This example creates a ci alias for the `git commit` command. You can then invoke `git commit` by executing `git ci`. Aliases can also reference other aliases to create powerful combos.



```
git config --global alias.amend ci --amend
```

This example creates an alias amend which composes the ci alias into a new alias that uses `--amend flag`.

## Formatting & whitespace

Git has several "whitespace" features that can be configured to highlight whitespace issues when using git diff. The whitespace issues will be highlighted using the configured color `color.diff.whitespace`

The following features are enabled by default:

- `blank-at-eol` highlights orphan whitespaces at the line endings
- `space-before-tab` highlights a space character that appears before a tab character when indenting a line
- `blank-at-eof` highlights blank lines inserted at the end of a file

The following features are disabled by default

- `indent-with-non-tab` highlights a line that is indented with spaces instead of tabs
- `tab-in-indent` highlights an initial tab indent as an error
- `trailing-space` is shorthand for both blank-at-eol and blank-at-eof
- `cr-at-eol highlights` a carriage-return at the line endings
- `tabwidth=<n>` defines how many character positions a tab occupies. The default value is 8. Allowed values are 1-63

## Summary

In this article, we covered the use of the git `config command`. We discussed how the command is a convince method for editing raw `git config` files on the filesystem. We looked at basic read and write operations for configuration options. We took a look at common config patterns:

- How to configure the Git editor
- How to override configuration levels
- How to reset configuration defaults
- How to customize git colors

Overall, `git config` is a helper tool that provides a shortcut to editing raw `git config` files on disk. We covered in depth personal customization options. Basic knowledge of git configuration options is a prerequisite for [setting up a repository](https://www.atlassian.com/git/tutorials/setting-up-a-repository). See our guide there for a demonstration of the basics.
