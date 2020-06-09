# Merging VS Rebasing

### 总结

rebase 使用的时机:

* 整理本地分支提交记录， 在当前分支上执行git rebase -i HEAD~n
* 整合上游的提交到本地分支

~~~bash
$ git log --oneline
122542a (HEAD -> master) b.txt
a889c11 (feature/reflog_test) replace 456 with abc
f690cab Revert "append 456 to a.txt"
541bf04 append 456 to a.txt
3d277e2 add 123 to a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/reflog_test)
$ git checkout -b feature/rebase_test
Switched to a new branch 'feature/rebase_test'

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ ls
a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ ls
a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ cat a.txt
123
abc

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ echo "rebace" >> a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ git ci -a
warning: LF will be replaced by CRLF in a.txt.
The file will have its original line endings in your working directory.
[feature/rebase_test be6adf6] a.txt
 1 file changed, 1 insertion(+)

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ git checkout master
Switched to branch 'master'

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ git checkout -b feature/merge_test
Switched to a new branch 'feature/merge_test'

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ echo "merge" >> a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git ci -a
warning: LF will be replaced by CRLF in a.txt.
The file will have its original line endings in your working directory.
[feature/merge_test 89bcee9] a.txt
 1 file changed, 1 insertion(+)

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git checkout master
Switched to branch 'master'

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ git status
On branch master
nothing to commit, working tree clean

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ ls
a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ ls
a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ echo "123" > b.txt

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ git add b.txt
warning: LF will be replaced by CRLF in b.txt.
The file will have its original line endings in your working directory.
g
lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ git commit
[master 122542a] b.txt
 1 file changed, 1 insertion(+)
 create mode 100644 b.txt

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ git checkout feature/merge_test
Switched to branch 'feature/merge_test'

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git merge master
Merge made by the 'recursive' strategy.
 b.txt | 1 +
 1 file changed, 1 insertion(+)
 create mode 100644 b.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git log
commit 1588ced008f1b2a868570073aa994ecf9c21d074 (HEAD -> feature/merge_test)
Merge: 89bcee9 122542a
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:25:59 2020 +0800

    Merge branch 'master' into feature/merge_test

commit 122542a4f0216107b40574662c239b2fdae9bf39 (master)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:25:37 2020 +0800

    b.txt

    -new file b.txt

commit 89bcee9ee36052295b33c707e55888bb03520858
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:24:36 2020 +0800

    a.txt

    - append merge to a.txt


lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git log --oneline --graphe
fatal: unrecognized argument: --graphe

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git log --oneline --graph
*   1588ced (HEAD -> feature/merge_test) Merge branch 'master' into feature/merg                                                      e_test
|\
| * 122542a (master) b.txt
* | 89bcee9 a.txt
|/
* a889c11 (feature/reflog_test) replace 456 with abc
* f690cab Revert "append 456 to a.txt"
* 541bf04 append 456 to a.txt
* 3d277e2 add 123 to a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git log
commit 1588ced008f1b2a868570073aa994ecf9c21d074 (HEAD -> feature/merge_test)
Merge: 89bcee9 122542a
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:25:59 2020 +0800

    Merge branch 'master' into feature/merge_test

commit 122542a4f0216107b40574662c239b2fdae9bf39 (master)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:25:37 2020 +0800

    b.txt

    -new file b.txt

commit 89bcee9ee36052295b33c707e55888bb03520858
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:24:36 2020 +0800

    a.txt

    - append merge to a.txt


lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git log --oneline --graph
*   1588ced (HEAD -> feature/merge_test) Merge branch 'master' into feature/merg                                                      e_test
|\
| * 122542a (master) b.txt
* | 89bcee9 a.txt
|/
* a889c11 (feature/reflog_test) replace 456 with abc
* f690cab Revert "append 456 to a.txt"
* 541bf04 append 456 to a.txt
* 3d277e2 add 123 to a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git checkout feature/rebase_test
feature/merge_test    feature/reflog_test   master
feature/rebase_test   HEAD                  ORIG_HEAD

lenovo@lenovo-PC MINGW64 /d/git_test (feature/merge_test)
$ git checkout feature/rebase_test
Switched to branch 'feature/rebase_test'

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ git rebase master
First, rewinding head to replay your work on top of it...
Applying: a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ git log --oneline
0d833e4 (HEAD -> feature/rebase_test) a.txt
122542a (master) b.txt
a889c11 (feature/reflog_test) replace 456 with abc
f690cab Revert "append 456 to a.txt"
541bf04 append 456 to a.txt
3d277e2 add 123 to a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ git log
commit 0d833e4ef3f8065bf17f08a1ea9864d80dd6fa8d (HEAD -> feature/rebase_test)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:23:46 2020 +0800

    a.txt

    -append "rebase" to a.txt

commit 122542a4f0216107b40574662c239b2fdae9bf39 (master)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Tue Mar 24 08:25:37 2020 +0800

    b.txt

    -new file b.txt

commit a889c114103fe17708d2b221585b452ed1bb9a05 (feature/reflog_test)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Fri Mar 20 11:21:59 2020 +0800

    replace 456 with abc

commit f690cab05d6b3fac988534526d1d788735960872

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ git log --oneline --graph
* 0d833e4 (HEAD -> feature/rebase_test) a.txt
* 122542a (master) b.txt
* a889c11 (feature/reflog_test) replace 456 with abc
* f690cab Revert "append 456 to a.txt"
* 541bf04 append 456 to a.txt
* 3d277e2 add 123 to a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (feature/rebase_test)
$ git checkout master
Switched to branch 'master'

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$ git log --oneline
122542a (HEAD -> master) b.txt
a889c11 (feature/reflog_test) replace 456 with abc
f690cab Revert "append 456 to a.txt"
541bf04 append 456 to a.txt
3d277e2 add 123 to a.txt

lenovo@lenovo-PC MINGW64 /d/git_test (master)
$

~~~



[Conceptual Overview](https://www.atlassian.com/git/tutorials/merging-vs-rebasing#conceptual-overview)[The Golden Rule of Rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing#the-golden-rule-of-rebasing)[Workflow Walkthrough](https://www.atlassian.com/git/tutorials/merging-vs-rebasing#workflow-walkthrough)[Summary](https://www.atlassian.com/git/tutorials/merging-vs-rebasing#summary)

The `git rebase` command has a reputation for being magical Git voodoo that beginners should stay away from, but it can actually make life much easier for a development team when used with care. In this article, we’ll compare `git rebase` with the related `git merge` command and identify all of the potential opportunities to incorporate rebasing into the typical Git workflow.

## Conceptual Overview

The first thing to understand about `git rebase` is that it solves the same problem as `git merge`. Both of these commands are designed to integrate changes from one branch into another branch—they just do it in very different ways.

Consider what happens when you start working on a new feature in a dedicated branch, then another team member updates the `master` branch with new commits. This results in a forked history, which should be familiar to anyone who has used Git as a collaboration tool.

![1584934394863](./${img}\1584934394863.png)
Now, let’s say that the new commits in `master` are relevant to the feature that you’re working on. To incorporate the new commits into your `feature` branch, you have two options: merging or rebasing.

### The Merge Option

The easiest option is to merge the `master` branch into the feature branch using something like the following:

```
git checkout feature
git merge master
```

Or, you can condense this to a one-liner:

```
git merge feature master
```

This creates a new “merge commit” in the `feature` branch that ties together the histories of both branches, giving you a branch structure that looks like this:

![1585013113338](./${img}\1585013113338.png)
Merging is nice because it’s a *non-destructive* operation. The existing branches are not changed in any way. This avoids all of the potential pitfalls of rebasing (discussed below).

On the other hand, this also means that the `feature` branch will have an extraneous merge commit every time you need to incorporate upstream changes. If `master` is very active, this can pollute your feature branch’s history quite a bit. While it’s possible to mitigate this issue with advanced `git log` options, it can make it hard for other developers to understand the history of the project.

### The Rebase Option

As an alternative to merging, you can rebase the `feature` branch onto `master` branch using the following commands:

```
git checkout feature
git rebase master 		#意思是将当前分支建立在master分支上
#将整个feature分支移动到master分支的顶端
```

This moves the entire `feature` branch to begin on the tip of the `master` branch, effectively incorporating all of the new commits in`master`. But, instead of using a merge commit, rebasing *re-writes *the project history by creating brand new commits for each commit in the original branch.

![1585010350589](./${img}\1585010350589.png)
The major benefit of rebasing is that you get a much cleaner project history. First, it eliminates the unnecessary merge commits required by `git merge`. Second, as you can see in the above diagram, rebasing also results in a perfectly linear project history—you can follow the tip of `feature` all the way to the beginning of the project without any forks. This makes it easier to navigate your project with commands like `git log`, `git bisect`, and `gitk`.

But, there are two trade-offs for this pristine commit history: safety and traceability. If you don’t follow the [Golden Rule of Rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing#the-golden-rule-of-rebasing), re-writing project history can be potentially catastrophic for your collaboration workflow. And, less importantly, rebasing loses the context provided by a merge commit—you can’t see when upstream changes were incorporated into the feature.

### <font color="green">Interactive Rebasing</font>

Interactive rebasing gives you the opportunity to alter commits as they are moved to the new branch. This is even more powerful than an automated rebase, since it offers complete control over the branch’s commit history. Typically, this is used to clean up a messy history before merging a feature branch into `master`.

To begin an interactive rebasing session, pass the `i` option to the `git rebase` command:

```
git checkout feature
git rebase -i master
```

This will open a text editor listing all of the commits that are about to be moved:

```
pick 33d5b7a Message for commit #1
pick 9480b3d Message for commit #2
pick 5c67e61 Message for commit #3
```

<font color="green">This listing defines exactly what the branch will look like after the rebase is performed. By changing the `pick` command and/or re-ordering the entries, you can make the branch’s history look like whatever you want. For example, if the 2nd commit fixes a small problem in the 1st commit, you can condense them into a single commit with the `fixup` command:</font>

```
pick 33d5b7a Message for commit #1
fixup 9480b3d Message for commit #2
pick 5c67e61 Message for commit #3
```

When you save and close the file, Git will perform the rebase according to your instructions, resulting in project history that looks like the following:

![1585010476225](./${img}\1585010476225.png)
Eliminating insignificant commits like this makes your feature’s history much easier to understand. This is something that `git merge` simply cannot do.

## <font color="green">The Golden Rule of Rebasing(黄金法则)</font>

<font color="green">Once you understand what rebasing is, the most important thing to learn is when *not* to do it. The golden rule of `git rebase` is to never use it on *public* branches.</font>

For example, think about what would happen if you rebased `master` onto your `feature` branch:

~~~
git checkout master
git rebase feature
~~~



![1585010530082](./${img}\1585010530082.png)
The rebase moves all of the commits in `master` onto the tip of `feature`. The problem is that this only happened in *your* repository. All of the other developers are still working with the original `master`. Since rebasing results in brand new commits, Git will think that your `master` branch’s history has diverged from everybody else’s.

The only way to synchronize the two `master` branches is to merge them back together, resulting in an extra merge commit *and* two sets of commits that contain the same changes (the original ones, and the ones from your rebased branch). Needless to say, this is a very confusing situation.

<font color="red">So, before you run `git rebase`, always ask yourself, “Is anyone else looking at this branch?” If the answer is yes, take your hands off the keyboard and start thinking about a non-destructive way to make your changes (e.g., the `git revert` command). Otherwise, you’re safe to re-write history as much as you like.</font>

### <font color="red">Force-Pushing</font>

If you try to push the rebased `master` branch back to a remote repository, Git will prevent you from doing so because it conflicts with the remote `master` branch. But, you can force the push to go through by passing the `--force` flag, like so:

```
# Be very careful with this command!
git push --force
```

This overwrites the remote `master` branch to match the rebased one from your repository and makes things very confusing for the rest of your team. So, be very careful to use this command only when you know exactly what you’re doing.

One of the only times you should be force-pushing is when you’ve performed a local cleanup *after* you’ve pushed a private feature branch to a remote repository (e.g., for backup purposes). This is like saying, “Oops, I didn’t really want to push that original version of the feature branch. Take the current one instead.” Again, it’s important that nobody is working off of the commits from the original version of the feature branch.

# Workflow Walkthrough 

Rebasing can be incorporated into your existing Git workflow as much or as little as your team is comfortable with. In this section, we’ll take a look at the benefits that rebasing can offer at the various stages of a feature’s development.

The first step in any workflow that leverages `git rebase` is to create a dedicated branch for each feature. This gives you the necessary branch structure to safely utilize rebasing:

![1585010767906](./${img}\1585010767906.png)


### Local Cleanup 使用的rebase的最佳时机

最佳时机即整理本地分支(未共享)的提交记录

<font color="green">One of the best ways to incorporate rebasing into your workflow is to clean up local, in-progress features. By periodically performing an interactive rebase, you can make sure each commit in your feature is focused and meaningful. This lets you write your code without worrying about breaking it up into isolated commits—you can fix it up after the fact.</font>

When calling `git rebase`, you have two options for the new base: The feature’s parent branch (e.g., `master`), or an earlier commit in your feature. We saw an example of the first option in the  *Interactive Rebasing* section. The latter option is nice when you only need to fix up the last few commits. For example, the following command begins an interactive rebase of only the last 3 commits.

```
git checkout feature
git rebase -i HEAD~3		# 意思是重新整理从HEAD开始的三次提交记录
```

<font color="blue">By specifying `HEAD~3` as the new base, you’re not actually moving the branch—you’re just interactively re-writing the 3 commits that follow it. Note that this will *not* incorporate upstream changes into the `feature` branch. </font>

![1585011052691](./${img}\1585011052691.png)


实例展示:

在本地的git仓库有a.txt文本文件，master分支的提交记录如下(master未共享):

~~~
$ git log --oneline
7e0f5cf (HEAD -> master) append abc to a.txt
ce538f8 append 789 to a.txt
79509c5 append 456 to a.txt
81ff20e write 123 to a.txt

~~~

执行git rebase -i HEAD~3后的结果:



![1585016955904](./${img}\1585016955904.png)


对图上内容进行如下修改:

~~~
pick 79509c5
pick ce538f8
pick 7e0f5cf
修改为:
pick 79509c5
squash ce538f8
squash 7e0f5cf
~~~

修改后保存并退出，会自动弹出下图。提示将三个提交合并成一个提交，编辑新的提交信息

![1585017057805](./${img}\1585017057805.png)


更改提交信息并保存后，可以通过git log看到三次提交合已经合并为一个提交

![1585017435709](./${img}\1585017435709.png)
<font color="green">If you want to re-write the entire feature using this method, the `git merge-base` command can be useful to find the original base of the `feature` branch. The following returns the commit ID of the original base, which you can then pass to `git rebase`: </font>

```
git merge-base feature master
```

This use of interactive rebasing is a great way to introduce `git rebase` into your workflow, as it only affects local branches. The only thing other developers will see is your finished product, which should be a clean, easy-to-follow feature branch history.

But again, this only works for *private* feature branches. If you’re collaborating with other developers via the same feature branch, that branch is *public*, and you’re not allowed to re-write its history.

There is no `git merge` alternative for cleaning up local commits with an interactive rebase.

### Incorporating Upstream Changes Into a Feature

In the *Conceptual Overview* section, we saw how a feature branch can incorporate upstream changes from `master` using either `git merge` or `git rebase`. Merging is a safe option that preserves the entire history of your repository, while rebasing creates a linear history by moving your feature branch onto the tip of `master`.

This use of `git rebase` is similar to a local cleanup (and can be performed simultaneously), but in the process it incorporates those upstream commits from `master`.

注意: 下面说的是same feature 而不是same branch

<font color="green">Keep in mind that it’s perfectly legal to rebase onto a remote branch instead of `master`. This can happen when collaborating on the same feature with another developer and you need to incorporate their changes into your repository.</font>

For example, if you and another developer named John added commits to the `feature` branch, your repository might look like the following after fetching the remote `feature` branch from John’s repository:

![1585011086600](./${img}\1585011086600.png)
You can resolve this fork the exact same way as you integrate upstream changes from `master`: either merge your local `feature`with `john/feature`, or rebase your local `feature` onto the tip of `john/feature`.



![1585011113599](./${img}\1585011113599.png)




![1585011146545](./${img}\1585011146545.png)
<font color="green">Note that this rebase doesn’t violate the *Golden Rule of Rebasing*  because only your local `feature` commits are being moved—everything before that is untouched. This is like saying, “add my changes to what John has already done.” In most circumstances, this is more intuitive than synchronizing with the remote branch via a merge commit.</font>

By default, the `git pull` command performs a merge, but you can force it to integrate the remote branch with a rebase by passing it the `--rebase` option.

### Reviewing a Feature With a Pull Request

If you use pull requests as part of your code review process, you need to avoid using `git rebase` after creating the pull request. As soon as you make the pull request, other developers will be looking at your commits, which means that it’s a *public* branch. Re-writing its history will make it impossible for Git and your teammates to track any follow-up commits added to the feature.

Any changes from other developers need to be incorporated with `git merge` instead of `git rebase`.

For this reason, it’s usually a good idea to clean up your code with an interactive rebase *before* submitting your pull request.



### <font color="green">Integrating an Approved Feature</font>

After a feature has been approved by your team, you have the option of rebasing the feature onto the tip of the `master` branch before using `git merge` to integrate the feature into the main code base.

This is a similar situation to incorporating upstream changes into a feature branch, but since you’re not allowed to re-write commits in the `master` branch, you have to eventually use `git merge` to integrate the feature. However, by performing a rebase before the merge, you’re assured that the merge will be fast-forwarded, resulting in a perfectly linear history. This also gives you the chance to squash any follow-up commits added during a pull request.

![1585011184312](./${img}\1585011184312.png)






![1585011203951](./${img}\1585011203951.png)




![1585011225887](./${img}\1585011225887.png)


If you’re not entirely comfortable with `git rebase`, you can always perform the rebase in a temporary branch. That way, if you accidentally mess up your feature’s history, you can check out the original branch and try again. For example:

```
git checkout feature
git checkout -b temporary-branch
git rebase -i master
# [Clean up the history]
git checkout master
git merge temporary-branch
```

## Summary

And that’s all you really need to know to start rebasing your branches. If you would prefer a clean, linear history free of unnecessary merge commits, you should reach for `git rebase`instead of `git merge` when integrating changes from another branch.

On the other hand, if you want to preserve the complete history of your project and avoid the risk of re-writing public commits, you can stick with `git merge`. Either option is perfectly valid, but at least now you have the option of leveraging the benefits of `git rebase`.