# git rebase





This document will serve as an in-depth discussion of the `git rebase` command. The Rebase command has also been looked at on the [setting up a repository](https://www.atlassian.com/git/tutorials/setting-up-a-repository) and [rewriting history](https://www.atlassian.com/git/tutorials/rewriting-history) pages. This page will take a more detailed look at `git rebase` configuration and execution. Common Rebase use cases and pitfalls will be covered here.

Rebase is one of two Git utilities that specializes in integrating changes from one branch onto another. The other change integration utility is `git merge`. Merge is always a forward moving change record. Alternatively, rebase has powerful history rewriting features. For a detailed look at Merge vs. Rebase, visit our [Merging vs Rebasing guide](https://www.atlassian.com/git/tutorials/merging-vs-rebasing). Rebase itself has 2 main modes: "manual" and "interactive" mode. We will cover the different Rebase modes in more detail below.

## What is git rebase?



Rebasing is the process of moving or combining a sequence of commits to a new base commit. Rebasing is most useful and easily visualized in the context of a feature branching workflow. The general process can be visualized as the following:



From a content perspective, rebasing is changing the base of your branch from one commit to another making it appear as if you'd created your branch from a different commit. Internally, Git accomplishes this by creating new commits and applying them to the specified base. It's very important to understand that even though the branch looks the same, it's composed of entirely new commits.

## Usage

The primary reason for rebasing is to maintain a linear project history. For example, consider a situation where the master branch has progressed since you started working on a feature branch. You want to get the latest updates to the master branch in your feature branch, but you want to keep your branch's history clean so it appears as if you've been working off the latest master branch. This gives the later benefit of a clean merge of your feature branch back into the master branch. Why do we want to maintain a "clean history"? The benefits of having a clean history become tangible when performing Git operations to investigate the introduction of a regression. A more real-world scenario would be:

1. A bug is identified in the master branch. A feature that was working successfully is now broken.
2. A developer examines the history of the master branch using `git log` because of the "clean history" the developer is quickly able to reason about the history of the project.
3. The developer can not identify when the bug was introduced using `git log` so the developer executes a `git bisect`.
4. Because the git history is clean, `git bisect` has a refined set of commits to compare when looking for the regression. The developer quickly finds the commit that introduced the bug and is able to act accordingly.

Learn more about [git log](https://www.atlassian.com/git/tutorials/git-log) and [git bisect](https://git-scm.com/docs/git-bisect) on their individual usage pages.

You have two options for integrating your feature into the master branch: merging directly or rebasing and then merging. The former option results in a 3-way merge and a merge commit, while the latter results in a fast-forward merge and a perfectly linear history. The following diagram demonstrates how rebasing onto the master branch facilitates a fast-forward merge.



Rebasing is a common way to integrate upstream changes into your local repository. Pulling in upstream changes with Git merge results in a superfluous merge commit every time you want to see how the project has progressed. On the other hand, rebasing is like saying, “I want to base my changes on what everybody has already done.”

### Don't rebase public history

As we've discussed previously in [rewriting history](https://www.atlassian.com/git/tutorials/rewriting-history), you should never rebase commits once they've been pushed to a public repository. The rebase would replace the old commits with new ones and it would look like that part of your project history abruptly vanished.

### Git Rebase Standard vs Git Rebase Interactive

Git rebase interactive is when git rebase accepts an `-- i` argument. This stands for "Interactive." Without any arguments, the command runs in standard mode. In both cases, let's assume we have created a separate feature branch.

```
# Create a feature branch based off of master 
git checkout -b feature_branch master 
# Edit files 
git commit -a -m "Adds new feature" 
```

Git rebase in standard mode will automatically take the commits in your current working branch and apply them to the head of the passed branch.

```
git rebase <base>
```

 

This automatically rebases the current branch onto `<base>`, which can be any kind of commit reference (for example an ID, a branch name, a tag, or a relative reference to `HEAD`).

Running `git rebase` with the `-i` flag begins an interactive rebasing session. Instead of blindly moving all of the commits to the new base, interactive rebasing gives you the opportunity to alter individual commits in the process. This lets you clean up history by removing, splitting, and altering an existing series of commits. It's like `Git commit --amend` on steroids.

```
git rebase --interactive <base>
```

 

This rebases the current branch onto `<base>` but uses an interactive rebasing session. This opens an editor where you can enter commands (described below) for each commit to be rebased. These commands determine how individual commits will be transferred to the new base. You can also reorder the commit listing to change the order of the commits themselves. Once you've specified commands for each commit in the rebase, Git will begin playing back commits applying the rebase commands. The rebasing edit commands are as follows:

```
pick 2231360 some old commit
pick ee2adc2 Adds new feature





# Rebase 2cf755d..ee2adc2 onto 2cf755d (9 commands)
#
# Commands:
# p, pick = use commit
# r, reword = use commit, but edit the commit message
# e, edit = use commit, but stop for amending
# s, squash = use commit, but meld into previous commit
# f, fixup = like "squash", but discard this commit's log message
# x, exec = run command (the rest of the line) using shell
# d, drop = remove commit
```

#### Additional rebase commands

As detailed in the [rewriting history page](https://www.atlassian.com/git/tutorials/rewriting-history), rebasing can be used to change older and multiple commits, committed files, and multiple messages. While these are the most common applications, `git rebase` also has additional command options that can be useful in more complex applications.

- `git rebase -- d` means during playback the commit will be discarded from the final combined commit block.
- `git rebase -- p` leaves the commit as is. It will not modify the commit's message or content and will still be an individual commit in the branches history.
- `git rebase -- x` during playback executes a command line shell script on each marked commit. A useful example would be to run your codebase's test suite on specific commits, which may help identify regressions during a rebase.

### Recap

Interactive rebasing gives you complete control over what your project history looks like. This affords a lot of freedom to developers, as it lets them commit a "messy" history while they're focused on writing code, then go back and clean it up after the fact.

Most developers like to use an interactive rebase to polish a feature branch before merging it into the main code base. This gives them the opportunity to squash insignificant commits, delete obsolete ones, and make sure everything else is in order before committing to the “official” project history. To everybody else, it will look like the entire feature was developed in a single series of well-planned commits.

The real power of interactive rebasing can be seen in the history of the resulting master branch. To everybody else, it looks like you're a brilliant developer who implemented the new feature with the perfect amount of commits the first time around. This is how interactive rebasing can keep a project's history clean and meaningful.

### Configuration options

There are a few rebase properties that can be set using `git config`. These options will alter the `git rebase` output look and feel.

- **rebase.stat**: A boolean that is set to false by default. The option toggles display of visual diffstat content that shows what changed since the last debase.

- **rebase.autoSquash:** A boolean value that toggles the `--autosquash` behavior.

- **rebase.missingCommitsCheck:** Can be set to multiple values which change rebase behavior around missing commits.

| `warn`   | Prints warning output in interactive mode which warns of removed commits |
| -------- | ------------------------------------------------------------ |
| `error`  | Stops the rebase and prints removed commit warning messages  |
| `ignore` | Set by default this ignores any missing commit warnings      |

- **rebase.instructionFormat:** A `git log` format string that will be used for formatting interactive rebase display

### Advanced rebase application

The command line argument` --onto` can be passed to `git rebase`. When in git rebase `--onto` mode the command expands to:

```
 git rebase --onto <newbase> <oldbase>
```

The `--onto` command enables a more powerful form or rebase that allows passing specific refs to be the tips of a rebase.
Let’s say we have an example repo with branches like:

```
   o---o---o---o---o master
        \
         o---o---o---o---o featureA
              \
               o---o---o featureB
```

 

featureB is based on featureA, however, we realize featureB is not dependent on any of the changes in featureA and could just be branched off master.

```
 git rebase --onto master featureA featureB
```

featureA is the `<oldbase>`. `master` becomes the `<newbase>` and featureB is reference for what `HEAD` of the `<newbase>` will point to. The results are then:

```
                      o---o---o featureB
                     /
    o---o---o---o---o master
     \
      o---o---o---o---o featureA
 
```

## Understanding the dangers of rebase

One caveat to consider when working with Git Rebase is merge conflicts may become more frequent during a rebase workflow. This occurs if you have a long-lived branch that has strayed from master. Eventually you will want to rebase against master and at that time it may contain many new commits that your branch changes may conflict with. This is easily remedied by rebasing your branch frequently against master, and making more frequent commits. The `--continue` and `--abort` command line arguments can be passed to `git rebase` to advance or reset the the rebase when dealing with conflicts.

A more serious rebase caveat is lost commits from interactive history rewriting. Running rebase in interactive mode and executing subcommands like squash or drop will remove commits from your branche's immediate log. At first glance this can appear as though the commits are permanently gone. Using `git reflog` these commits can be restored and the entire rebase can be undone. For more info on using `git reflog` to find lost commits, visit our [Git reflog documentation page](https://www.atlassian.com/git/tutorials/rewriting-history/git-reflog).

Git Rebase itself is not seriously dangerous. The real danger cases arise when executing history rewriting interactive rebases and force pushing the results to a remote branch that's shared by other users. This is a pattern that should be avoided as it has the capability to overwrite other remote users' work when they pull.

## Recovering from upstream rebase

If another user has rebased and force pushed to the branch that you’re committing to, a `git pull` will then overwrite any commits you have based off that previous branch with the tip that was force pushed. Luckily, using `git reflog` you can get the reflog of the remote branch. On the remote branch's reflog you can find a ref before it was rebased. You can then rebase your branch against that remote ref using the `--onto` option as discussed above in the Advanced Rebase Application section.

## Summary

In this article we covered `git rebase` usage. We discussed basic and advanced use cases and more advanced examples. Some key discussion points are:

- git rebase standard vs interactive modes
- git rebase configuration options
- git rebase --onto
- git rebase lost commits

We looked at `git rebase` usage with other tools like [`git reflog`](https://www.atlassian.com/git/tutorials/rewriting-history/git-reflog), [`git fetch`](https://www.atlassian.com/git/tutorials/syncing#git-fetch), and [`git push`](https://www.atlassian.com/git/tutorials/syncing#git-push). Visit their corresponding pages for further information.