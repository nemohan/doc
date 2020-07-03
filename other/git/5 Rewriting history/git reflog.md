# git reflog

[TOC]

引用日志

记录引用更改的日志,可以用来恢复丢失的commit记录

This page provides a detailed discussion of the `git reflog` command. Git keeps track of updates to the tip of branches using a mechanism called reference logs, or "reflogs." Many Git commands accept a parameter for specifying a reference or "ref", which is a pointer to a commit. Common examples include:

- `git checkout`
- `git reset`
- `git merge`

<font color="red">Reflogs track when Git refs were updated in the local repository. In addition to branch tip reflogs, a special reflog is maintained for the Git stash. Reflogs are stored in directories under the local repository's `.git` directory. `git reflog` directories can be found at `.git/logs/refs/heads/.`, `.git/logs/HEAD`, and also `.git/logs/refs/stash` if the `git stash` has been used on the repo.</font>

We discussed `git reflog` at a high level on the [Rewriting History Page](https://www.atlassian.com/git/tutorials/rewriting-history). This document will cover: extended configuration options of `git reflog`, common use-cases and pitfalls of `git reflog`, how to undo changes with `git reflog`, and more.

## Basic usage

The most basic Reflog use case is invoking:

```
git reflog
```

This is essentially a short cut that's equivalent to:

```
git reflog show HEAD
```

This will output the `HEAD` reflog(the content in .git/logs/HEAD). You should see output similar to:

```
eff544f HEAD@{0}: commit: migrate existing content
bf871fd HEAD@{1}: commit: Add Git Reflog outline
9a4491f HEAD@{2}: checkout: moving from master to git_reflog
9a4491f HEAD@{3}: checkout: moving from Git_Config to master
39b159a HEAD@{4}: commit: expand on git context 
9b3aa71 HEAD@{5}: commit: more color clarification
f34388b HEAD@{6}: commit: expand on color support 
9962aed HEAD@{7}: commit: a git editor -> the Git editor
```

Visit the [Rewriting History page](https://www.atlassian.com/git/tutorials/rewriting-history) for another example of common reflog access.

### Reflog references

<font color="red">By default, `git reflog` will output the reflog of the `HEAD` ref. `HEAD` is a symbolic reference to the currently active branch. Reflogs are available for other refs as well. The syntax to access a git ref is `name@{qualifier}`. In addition to `HEAD` refs, other branches, tags, remotes, and the Git stash can be referenced as well.</font>

You can get a complete reflog of all refs by executing:

```
 git reflog show --all
```

To see the reflog for a specific branch pass that branch name to `git reflog show`

```bash
git reflog show otherbranch

9a4491f otherbranch@{0}: commit: seperate articles into branch PRs
35aee4a otherbranch{1}: commit (initial): initial commit add git-init and setting-up-a-repo docs
```

Executing this example will show a reflog for the `otherbranch` branch. The following example assumes you have previously stashed some changes using the `git stash` command.

```
git reflog stash

0d44de3 stash@{0}: WIP on git_reflog: c492574 flesh out intro
```

This will output a reflog for the Git stash. The returned ref pointers can be passed to other Git commands:

```
git diff stash@{0} otherbranch@{0}
```

When executed, this example code will display Git diff output comparing the `stash@{0}` changes against the `otherbranch@{0}` ref.

### Timed reflogs

Every reflog entry has a timestamp attached to it. These timestamps can be leveraged as the `qualifier` token of Git ref pointer syntax. This enables filtering Git reflogs by time. The following are some examples of available time qualifiers:

- `1.minute.ago`
- `1.hour.ago`
- `1.day.ago`
- `yesterday`
- `1.week.ago`
- `1.month.ago`
- `1.year.ago`
- `2011-05-17.09:00:00`

Time qualifiers can be combined (e.g. `1.day.2.hours.ago`), Additionally plural forms are accepted (e.g. `5.minutes.ago`).

Time qualifier refs can be passed to other git commands.

```
 git diff master@{0} master@{1.day.ago}
```

This example will diff the current master branch against master 1 day ago. This example is very useful if you want to know changes that have occurred within a time frame.

## Subcommands & configuration options

`git reflog` accepts few addition arguments which are considered subcommands.

### Show - `git reflog show`

`show` is implicitly passed by default. For example, the command:

```
git reflog master@{0}
```

is equivalent to the command:

```
git reflog show master@{0}
```

In addition, `git reflog show` is an alias for `git log -g --abbrev-commit --pretty=oneline`. Executing `git reflog show` will display the log for the passed <refid>.``



### Expire - `git reflog expire`

<font color="green">The expire subcommand cleans up old or unreachable reflog entries. The `expire` subcommand has potential for data loss. This subcommand is not typically used by end users, but used by git internally. Passing a `-n` or `--dry-run` option to `git reflog expire` Will perform a "dry run" which will output which reflog entries are marked to be pruned, but will not actually prune them.</font>

By default, the reflog expiration date is set to 90 days. An expire time can be specified by passing a command line argument `--expire=time` to `git reflog expire` or by setting a git configuration name of `gc.reflogExpire`.

### Delete - `git reflog delete`

The `delete` subcommand is self explanatory and will delete a passed in reflog entry. As with `expire`, `delete` has potential to lose data and is not commonly invoked by end users.





## <font color="red">Recovering lost commits</font>

Git never really loses anything, even when performing history rewriting operations like rebasing or commit amending. For the next example let's assume that we have made some new changes to our repo. Our `git log --pretty=oneline` looks like the following:

```
338fbcb41de10f7f2e54095f5649426cb4bf2458 extended content
1e63ceab309da94256db8fb1f35b1678fb74abd4 bunch of content
c49257493a95185997c87e0bc3a9481715270086 flesh out intro
eff544f986d270d7f97c77618314a06f024c7916 migrate existing content
bf871fd762d8ef2e146d7f0226e81a92f91975ad Add Git Reflog outline
35aee4a4404c42128bee8468a9517418ed0eb3dc initial commit add git-init and setting-up-a-repo docs
```

We then commit those changes and execute the following:

```
#make changes to HEAD
git commit -am "some WIP changes"
```

With the addition of the new commit. The log now looks like:

```bash
37656e19d4e4f1a9b419f57850c8f1974f871b07 some WIP changes
338fbcb41de10f7f2e54095f5649426cb4bf2458 extended content
1e63ceab309da94256db8fb1f35b1678fb74abd4 bunch of content
c49257493a95185997c87e0bc3a9481715270086 flesh out intro
eff544f986d270d7f97c77618314a06f024c7916 migrate existing content
bf871fd762d8ef2e146d7f0226e81a92f91975ad Add Git Reflog outline
35aee4a4404c42128bee8468a9517418ed0eb3dc initial commit add git-init and setting-up-a-repo docs
```

At this point we perform an interactive rebase against the master branch by executing...

```bash
git rebase -i origin/master
```

During the rebase we mark commits for squash with the `s` rebase subcommand. During the rebase, we squash a few commits into the most recent "some WIP changes" commit.

Because we squashed commits the `git log` output now looks like:

```
40dhsoi37656e19d4e4f1a9b419f57850ch87dah987698hs some WIP changes
35aee4a4404c42128bee8468a9517418ed0eb3dc initial commit add git-init and setting-up-a-repo docs
```

If we examine `git log` at this point it appears that we no longer have the commits that were marked for squashing. What if we want to operate on one of the squashed commits? Maybe to remove its changes from history? This is an opportunity to leverage the reflog.

```bash
git reflog
37656e1 HEAD@{0}: rebase -i (finish): returning to refs/heads/git_reflog
37656e1 HEAD@{1}: rebase -i (start): checkout origin/master
37656e1 HEAD@{2}: commit: some WIP changes
```

We can see there are reflog entries for the start and finish of the `rebase` and prior to those is our "some WIP changes" commit. We can pass the reflog ref to `git reset` and reset to a commit that was before the rebase.

```
git reset HEAD@{2}
```

Executing this reset command will move `HEAD` to the commit where "some WIP changes" was added, essentially restoring the other squashed commits.

## Summary

In this tutorial we discussed the `git reflog` command. Some key points covered were:

- How to view reflog for specific branches
- How to undo a git rebase using the reflog
- How specify and view time based reflog entries

We briefly mentioned that `git reflog` can be used with other git commands like [git checkout](https://www.atlassian.com/git/tutorials/using-branches#git-checkout), [git reset](https://www.atlassian.com/git/tutorials/resetting-checking-out-and-reverting), and [git merge](https://www.atlassian.com/git/tutorials/git-merge). Learn more at their respective pages. For additional discussion on refs and the reflog, [learn more here](https://www.atlassian.com/git/tutorials/refs-and-the-reflog).
