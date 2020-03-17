# merge strategies

# Git Merge Strategy Options and Examples

When a piece of work is complete, tested and ready to be merged back into the main line of development, your team has some policy choices to make. What are your merge strategy options? In this article we'll examine the possibilities and then provide some notes on how Atlassian operates. Hopefully at the end you'll have the tools to decide what works best for your team.

## Git Merge Strategies

A merge happens when combining two branches. Git will take two (or more) commit pointers and attempt to find a common base commit between them. Git has several different methods to find a base commit, these methods are called "merge strategies". Once Git finds a common base commit it will create a new "merge commit" that combines the changes of the specified merge commits. Technically, a merge commit is a regular commit which just happens to have two parent commits.



`git merge` will automatically select a merge strategy unless explicitly specified. The `git merge` and `git pull` commands can be passed an `-s` (strategy) option. The `-s` option can be appended with the name of the desired merge strategy. If not explicitly specified, Git will select the most appropriate merge strategy based on the provided branches. The following is a list of the available merge strategies.

### Recursive

```
git merge -s recursive branch1 branch2
```

This operates on two heads. Recursive is the default merge strategy when pulling or merging one branch. Additionally this can detect and handle merges involving renames, but currently cannot make use of detected copies. This is the default merge strategy when pulling or merging one branch.

### Resolve

```
git merge -s resolve branch1 branch2
```

This can only resolve two heads using a 3-way merge algorithm. It tries to carefully detect cris-cross merge ambiguities and is considered generally safe and fast.

### Octopus

```
git merge -s octopus branch1 branch2 branch3 branchN
```

The default merge strategy for more than two heads. When more than one branch is passed octopus is automatically engaged. If a merge has conflicts that need manual resolution octopus will refuse the merge attempt. It is primarily used for bundling similar feature branch heads together.

### Ours

```
git merge -s ours branch1 branch2 branchN
```

The Ours strategy operates on multiple N number of branches. The output merge result is always that of the current branch `HEAD`. The "ours" term implies the preference effectively ignoring all changes from all other branches. It is intended to be used to combine history of similar feature branches.

### Subtree

```
git merge -s subtree branchA branchB
```

This is an extension of the recursive strategy. When merging A and B, if B is a child subtree of A, B is first updated to reflect the tree structure of A, This update is also done to the common ancestor tree that is shared between A and B.

## Types of Git Merge Strategies

### Explicit Merges

Explicit merges are the default merge type. The 'explicit' part is that they create a new merge commit. This alters the commit history and explicitly shows where a merge was executed. The merge commit content is also explicit in the fact that it shows which commits were the parents of the merge commit. Some teams avoid explicit merges because arguably the merge commits add "noise" to the history of the project.

### `implicit merge via rebase or fast-forward merge`

Whereas explicit merges create a merge commit, implicit merges do not. An implicit merge takes a series of commits from a specified branch head and applies them to the top of a target branch. Implicit merges are triggered by [rebase events](https://www.atlassian.com/git/tutorials/rewriting-history/git-rebase), or [fast forward merges](https://www.atlassian.com/git/tutorials/using-branches/git-merge). An implicit merge is an ad-hoc selection of commits from a specified branch.

### Squash on merge, generally without explicit merge

Another type of implicit merge is a squash. A squash can be performed during an [interactive rebase](https://www.atlassian.com/git/tutorials/rewriting-history/git-rebase). A squash merge will take the commits from a target branch and combine or squash them in to one commit. This commit is then appended to the `HEAD` of the merge base branch. A squash is commonly used to keep a 'clean history' during a merge. The target merge branch can have a verbose history of frequent commits. When squashed and merged the target branches commit history then becomes a singular squashed 'branch commit'. This technique is useful with `git workflows` that utilize feature branches.

## `git checkout master Switched to branch 'master' echo "content to append" >> merge.txt git commit -am"appended content to merge.txt" [master 24fbe3c] appended content to merge.tx 1 file changed, 1 insertion(+)`

The 'recursive' strategy introduced above, has its own subset of additional operation options.

```
ours
```

Not to be confused with the Ours merge strategy. This option conflicts to be auto-resolved cleanly by favoring the 'our' version. Changes from the 'theirs' side are automatically incorporated if they do not conflict.

```
theirs
```

The opposite of the 'ours' strategy. the "theirs" option favors the foreign merging tree in conflict resolution.

```
patience
```

This option spends extra time to avoid mis-merges on unimportant matching lines. This options is best used when branches to be merged have extremely diverged.

```
diff-algorithim
```

This option allows specification of an explicit diff-algorithim. The diff-algorithims are shared with the `git diff` command.

```
ignore-*

 ignore-space-change
 ignore-all-space
 ignore-space-at-eol
 ignore-cr-at-eol
```

A set of options that target whitespace characters. Any line that matches the subset of the passed option will be ignored.

```
renormalize
```

This option runs a check-out and check-in on all of the tree git trees while resolving a three-way merge. This option is intended to be used with merging branches with differing `checkin`/`checkout` states.

```
no-normalize
```

Disables the renormalize option. This overrides the `merge.renormalize` configuration variable.

```
no-renames
```

This option will ignore renamed files during the merge.

```
find-renames=n
```

This is the default behavior. The recursive merge will honor file renames. The `n` parameter can be used to pass a threshold for rename similarity. The default `n` value is `100%.`

```
subtree
```

This option borrows from the `subtree` strategy. Where the strategy operates on two trees and modifies how to make them match on a shared ancestor, this option instead operates on the path metadata of the tree to make them match.

## Our Git Merge Policy

Atlassian strongly prefers using explicit merges. The reason is very simple: explicit merges provide great traceability and context on the features being merged. A local history clean-up rebase before sharing a feature branch for review is absolutely encouraged, but this does not change the policy at all. It augments it.

Ready to try branching?

Try this interactive tutorial.

Get started now



![Git merge](https://www.atlassian.com/dam/jcr:389059a7-214c-46a3-bc52-7781b4730301/hero.svg)

##### Next up:

#### Comparing Workflows

START NEXT TUTORIAL