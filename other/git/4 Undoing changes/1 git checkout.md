# git checkout

### 改写历史，重回过去

改写历史的几种方式:

##### git checkout



当前提交记录

~~~
ab19d3c (HEAD -> master) Revert "修改a.txt"
b028812 (tag: v1.0) 修改a.txt
baf7b1d 修改a.txt
3165925 add data 123 to a.txt
224e1e5 add a.txt

~~~



在当前分支(master)执行 git checkout commit，会出现如下提示

~~~bash

$ git checkout 3165925551f3892a56d091d5bb3fd8a50352f9b7
Note: checking out '3165925551f3892a56d091d5bb3fd8a50352f9b7'.

You are in 'detached HEAD' state. You can look around, make experimental
changes and commit them, and you can discard any commits you make in this
state without impacting any branches by performing another checkout.

If you want to create a new branch to retain commits you create, you may
do so (now or later) by using -b with the checkout command again. Example:

  git checkout -b <new-branch-name>

HEAD is now at 3165925... add data 123 to a.txt

~~~

意思是当前处于'detached HEAD'状态，"分离的HEAD"什么意思？？。未执行上述命令前.git/HEAD文件的内容为refs/heads/master。执行checkout命令后, .git/HEAD文件内容为365925...，.git/refs/heads/master仍指向提交ab19d3。

在这种状态下，如果直接切到其他分支，新的提交会被丢弃，若要保留提交，可以新建分支

~~~bash
echo "abc" > a.txt
git add a.txt
git commit -m "replace 123 with abc"
git checkout master //导致当前的提及被丢弃

git checkout -b new_branch 会保留当前提交
~~~



<font color="red">这种回退的方式适用于回到过去的某个提交点，然后在此提交点上创建新的分支。在原分支上checkout commit的以后的提交历史在新分支上都被丢弃了</font>

##### git revert  

git revert 是更改已经共享的commit的最佳方法，即已经使用push 推送到了远程仓库。因为git revert 会撤销某次提交的内容并生成一个新的commit。相当于对某次提交的内容做了一次undo，但提交历史还保留着，并为这次undo生成新的提交。

~~~
git revert <commit>
~~~



##### git reset

更改本地未共享的commit的最佳方法。git reset的使用方式

~~~
git reset --mixed	重置HEAD和index, 当前工作区不变
git reset --hard	重置HEAD、index, 当前工作区
git reset --soft 	重置HEAD
git reset --merge	重置HEAD、index、当前工作区。git reset --merge 和--hard的区别是啥
git reset --keep	重置HEAD but keep local changes

~~~

以上几种使用方式的区别如下:

~~~bash
lenovo@lenovo-PC MINGW64 /d/git_pra (master)
$ echo "123" > a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (master)

$ git add a.txt
warning: LF will be replaced by CRLF in a.txt.
The file will have its original line endings in your working directory.
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (master)

$ git commit -m "write 123 to a.txt"
[master (root-commit) a29d97a] write 123 to a.txt
 1 file changed, 1 insertion(+)
 create mode 100644 a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (master)

$ echo "456" >> a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (master)
$ cat a.txt
123
456
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (master)
$ git commit -am "append 456 to a.txt"
warning: LF will be replaced by CRLF in a.txt.
The file will have its original line endings in your working directory.
[master 47e90f8] append 456 to a.txt
 1 file changed, 1 insertion(+)
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (master)
$ git log -2
commit 47e90f862f7b83eda57a7ff01ee111591220161e (HEAD -> master)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:47:25 2020 +0800

    append 456 to a.txt

commit a29d97a3f1f4eaaaf9994326aabdf7c816e168ee
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:46:52 2020 +0800

    write 123 to a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (master)



~~~

~~~


~~~





--mixed 选项

~~~bash
$ git log
commit 47e90f862f7b83eda57a7ff01ee111591220161e (HEAD -> feature/test_reset_mixed, master)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:47:25 2020 +0800

    append 456 to a.txt

commit a29d97a3f1f4eaaaf9994326aabdf7c816e168ee
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:46:52 2020 +0800

    write 123 to a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ cat a.txt
123
456
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ echo "789" >> a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ git add a.txt
warning: LF will be replaced by CRLF in a.txt.
The file will have its original line endings in your working directory.
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ git status
On branch feature/test_reset_mixed
Changes to be committed:
  (use "git reset HEAD <file>..." to unstage)

        modified:   a.txt

g(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ git reset --mixed a29d97
Unstaged changes after reset:
M       a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ cat a.txt
123
456
789
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ git status
On branch feature/test_reset_mixed
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git checkout -- <file>..." to discard changes in working directory)

        modified:   a.txt

no changes added to commit (use "git add" and/or "git commit -a")
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$

lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_mixed)
$ git log
commit a29d97a3f1f4eaaaf9994326aabdf7c816e168ee (HEAD -> feature/test_reset_mixed)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:46:52 2020 +0800

    write 123 to a.txt
(venv)


~~~



--hard

~~~bash
$ git checkout -b feature/test_reset_hard
Switched to a new branch 'feature/test_reset_hard'
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_hard)
$ cat a.txt
123
456
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_hard)
$ git log
commit 47e90f862f7b83eda57a7ff01ee111591220161e (HEAD -> feature/test_reset_hard, master)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:47:25 2020 +0800

    append 456 to a.txt

commit a29d97a3f1f4eaaaf9994326aabdf7c816e168ee (feature/test_reset_mixed)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:46:52 2020 +0800

    write 123 to a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_hard)
$ echo "789" >> a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_hard)
$ git reset --hard a29d97
HEAD is now at a29d97a write 123 to a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_hard)
$ git log
commit a29d97a3f1f4eaaaf9994326aabdf7c816e168ee (HEAD -> feature/test_reset_hard, feature/test_reset_mixed)
Author: hanzhao6L <hanzhao@vipiao.com>
Date:   Thu Mar 19 22:46:52 2020 +0800

    write 123 to a.txt
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_hard)
$ cat a.txt
123
(venv)
lenovo@lenovo-PC MINGW64 /d/git_pra (feature/test_reset_hard)
$

~~~

<font color="red">通过对比使用git reset --hard 和git reset --mixed，将二者的区别更加清晰的展示出来。不过还有个疑问重置index, 此处的index指什么，有什么用途</font>

### 更改工作区和暂存区



# Undoing Commits & Changes

[git checkout](https://www.atlassian.com/git/tutorials/undoing-changes)[git clean](https://www.atlassian.com/git/tutorials/undoing-changes/git-clean)[git revert](https://www.atlassian.com/git/tutorials/undoing-changes/git-revert)[git reset](https://www.atlassian.com/git/tutorials/undoing-changes/git-reset)[git rm](https://www.atlassian.com/git/tutorials/undoing-changes/git-rm)

In this section, we will discuss the available 'undo' Git strategies and commands. It is first important to note that Git does not have a traditional 'undo' system like those found in a word processing application. It will be beneficial to refrain from mapping Git operations to any traditional 'undo' mental model. Additionally, Git has its own nomenclature for 'undo' operations that it is best to leverage in a discussion. This nomenclature includes terms like reset, revert, checkout, clean, and more.

A fun metaphor is to think of Git as a timeline management utility. Commits are snapshots of a point in time or points of interest along the timeline of a project's history. Additionally, multiple timelines can be managed through the use of branches. When 'undoing' in Git, you are usually moving back in time, or to another timeline where mistakes didn't happen.

This tutorial provides all of the necessary skills to work with previous revisions of a software project. First, it shows you how to explore old commits, then it explains the difference between reverting public commits in the project history vs. resetting unpublished changes on your local machine.

## Finding what is lost: Reviewing old commits

The whole idea behind any version control system is to store “safe” copies of a project so that you never have to worry about irreparably breaking your code base. Once you’ve built up a project history of commits, you can review and revisit any commit in the history. One of the best utilities for reviewing the history of a Git repository is the `git log` command. In the example below, we use `git log` to get a list of the latest commits to a popular open-source graphics library.

```
git log --oneline
e2f9a78fe Replaced FlyControls with OrbitControls
d35ce0178 Editor: Shortcuts panel Safari support.
9dbe8d0cf Editor: Sidebar.Controls to Sidebar.Settings.Shortcuts. Clean up.
05c5288fc Merge pull request #12612 from TyLindberg/editor-controls-panel
0d8b6e74b Merge pull request #12805 from harto/patch-1
23b20c22e Merge pull request #12801 from gam0022/improve-raymarching-example-v2
fe78029f1 Fix typo in documentation
7ce43c448 Merge pull request #12794 from WestLangley/dev-x
17452bb93 Merge pull request #12778 from OndrejSpanel/unitTestFixes
b5c1b5c70 Merge pull request #12799 from dhritzkiv/patch-21
1b48ff4d2 Updated builds.
88adbcdf6 WebVRManager: Clean up.
2720fbb08 Merge pull request #12803 from dmarcos/parentPoseObject
9ed629301 Check parent of poseObject instead of camera
219f3eb13 Update GLTFLoader.js
15f13bb3c Update GLTFLoader.js
6d9c22a3b Update uniforms only when onWindowResize
881b25b58 Update ProjectionMatrix on change aspect
```

Each commit has a unique SHA-1 identifying hash. These IDs are used to travel through the committed timeline and revisit commits. By default, `git log` will only show commits for the currently selected branch. It is entirely possible that the commit you're looking for is on another branch. You can view all commits across all branches by executing `git log --branches=*`. The command `git branch` is used to view and visit other branches. Invoking the command, `git branch -a` will return a list of all known branch names. One of these branch names can then be logged using `git log <branch_name>`.

<font color="red">When you have found a commit reference to the point in history you want to visit, you can utilize the `git checkout` command to visit that commit. `Git checkout` is an easy way to “load” any of these saved snapshots onto your development machine. During the normal course of development, the `HEAD` usually points to `master` or some other local branch, but when you check out a previous commit, `HEAD` no longer points to a branch—it points directly to a commit. This is called a “detached `HEAD`” state, and it can be visualized as the following:</font>



Checking out an old file does not move the `HEAD` pointer. It remains on the same branch and same commit, avoiding a 'detached head' state. You can then commit the old version of the file in a new snapshot as you would any other changes. So, in effect, this usage of `git checkout` on a file, serves as a way to revert back to an old version of an individual file. For more information on these two modes visit the `git checkout` page

## Viewing an old revision

This example assumes that you’ve started developing a crazy experiment, but you’re not sure if you want to keep it or not. To help you decide, you want to take a look at the state of the project before you started your experiment. First, you’ll need to find the ID of the revision you want to see.

```
git log --oneline
```

Let’s say your project history looks something like the following:

```
b7119f2 Continue doing crazy things
872fa7e Try something crazy
a1e8fb5 Make some important changes to hello.txt
435b61d Create hello.txt
9773e52 Initial import
```

You can use `git checkout` to view the “Make some import changes to hello.txt” commit as follows:

```
git checkout a1e8fb5
```

This makes your working directory match the exact state of the `a1e8fb5` commit. You can look at files, compile the project, run tests, and even edit files without worrying about losing the current state of the project. Nothing you do in here will be saved in your repository. To continue developing, you need to get back to the “current” state of your project:

```
git checkout master
```

This assumes that you're developing on the default `master` branch. Once you’re back in the `master` branch, you can use either `git revert `or `git reset` to undo any undesired changes.

## Undoing a committed snapshot

There are technically several different strategies to 'undo' a commit. The following examples will assume we have a commit history that looks like:

```
git log --oneline
872fa7e Try something crazy
a1e8fb5 Make some important changes to hello.txt
435b61d Create hello.txt
9773e52 Initial import
```

We will focus on undoing the `872fa7e Try something crazy` commit. Maybe things got a little too crazy.

## <font color="red">How to undo a commit with git checkout</font>

Using the `git checkout` command we can checkout the previous commit, `a1e8fb5,` putting the repository in a state before the crazy commit happened. Checking out a specific commit will put the repo in a "detached HEAD" state. This means you are no longer working on any branch. In a detached state, any new commits you make will be orphaned when you change branches back to an established branch. Orphaned commits are up for deletion by Git's garbage collector. The garbage collector runs on a configured interval and permanently destroys orphaned commits. To prevent orphaned commits from being garbage collected, we need to ensure we are on a branch.

From the detached HEAD state, we can execute `git checkout -b new_branch_without_crazy_commit`. This will create a new branch named `new_branch_without_crazy_commit` and switch to that state. The repo is now on a new history timeline in which the `872fa7e` commit no longer exists. At this point, we can continue work on this new branch in which the `872fa7e` commit no longer exists and consider it 'undone'. Unfortunately, if you need the previous branch, maybe it was your `master` branch, this undo strategy is not appropriate. Let's look at some other 'undo' strategies. For more information and examples review our in-depth `git checkout` discussion.

## How to undo a public commit with git revert

Let's assume we are back to our original commit history example. The history that includes the `872fa7e` commit. This time let's try a revert 'undo'. If we execute `git revert HEAD`, Git will create a new commit with the inverse of the last commit. This adds a new commit to the current branch history and now makes it look like:

```
git log --oneline
e2f9a78 Revert "Try something crazy"
872fa7e Try something crazy
a1e8fb5 Make some important changes to hello.txt
435b61d Create hello.txt
9773e52 Initial import
```

At this point, we have again technically 'undone' the `872fa7e` commit. Although `872fa7e` still exists in the history, the new `e2f9a78` commit is an inverse of the changes in `872fa7e`. Unlike our previous checkout strategy, we can continue using the same branch. This solution is a satisfactory undo. This is the ideal 'undo' method for working with public shared repositories. If you have requirements of keeping a curated and minimal Git history this strategy may not be satisfactory.

## How to undo a commit with git reset

For this undo strategy we will continue with our working example. `git reset` is an extensive command with multiple uses and functions. If we invoke `git reset --hard a1e8fb5` the commit history is reset to that specified commit. Examining the commit history with `git log` will now look like:

```
git log --oneline
a1e8fb5 Make some important changes to hello.txt
435b61d Create hello.txt
9773e52 Initial import
```

The log output shows the `e2f9a78` and `872fa7e` commits no longer exist in the commit history. At this point, we can continue working and creating new commits as if the 'crazy' commits never happened. This method of undoing changes has the cleanest effect on history. Doing a reset is great for local changes however it adds complications when working with a shared remote repository. If we have a shared remote repository that has the `872fa7e` commit pushed to it, and we try to `git push` a branch where we have reset the history, Git will catch this and throw an error. Git will assume that the branch being pushed is not up to date because of it's missing commits. In these scenarios, `git revert` should be the preferred undo method.

## Undoing the last commit

In the previous section, we discussed different strategies for undoing commits. These strategies are all applicable to the most recent commit as well. In some cases though, you might not need to remove or reset the last commit. Maybe it was just made prematurely. In this case you can amend the most recent commit. Once you have made more changes in the working directory and staged them for commit by using `git add`, you can execute `git commit --amend`. This will have Git open the configured system editor and let you modify the last commit message. The new changes will be added to the amended commit.



## <font color="red">Undoing uncommitted changes</font>

Before changes are committed to the repository history, they live in the staging index and the working directory. You may need to undo changes within these two areas. The staging index and working directory are internal Git state management mechanisms. For more detailed information on how these two mechanisms operate, visit the `git reset` page which explores them in depth.

## The working directory

The working directory is generally in sync with the local file system. To undo changes in the working directory you can edit files like you normally would using your favorite editor. Git has a couple utilities that help manage the working directory. There is the `git clean` command which is a convenience utility for undoing changes to the working directory. Additionally, `git reset` can be invoked with the `--mixed` or `--hard` options and will apply a reset to the working directory.

## The staging index

The `git add` command is used to add changes to the staging index. `Git reset` is primarily used to undo the staging index changes. A `--mixed` reset will move any pending changes from the staging index back into the working directory.

## Undoing public changes

When working on a team with remote repositories, extra consideration needs to be made when undoing changes. `Git reset` should generally be considered a 'local' undo method. A reset should be used when undoing changes to a private branch. This safely isolates the removal of commits from other branches that may be in use by other developers. Problems arise when a reset is executed on a shared branch and that branch is then pushed remotely with `git push`. Git will block the push in this scenario complaining that the branch being pushed is out of date from the remote branch as it is missing commits.

The preferred method of undoing shared history is `git revert`. A revert is safer than a reset because it will not remove any commits from a shared history. A revert will retain the commits you want to undo and create a new commit that inverts the undesired commit. This method is safer for shared remote collaboration because a remote developer can then pull the branch and receive the new revert commit which undoes the undesired commit.

## Summary

We covered many high-level strategies for undoing things in Git. It's important to remember that there is more than one way to 'undo' in a Git project. Most of the discussion on this page touched on deeper topics that are more thoroughly explained on pages specific to the relevant Git commands. The most commonly used 'undo' tools are `git checkout, git revert`, and `git reset`. Some key points to remember are:

- Once changes have been committed they are generally permanent
- Use `git checkout` to move around and review the commit history
- `git revert` is the best tool for undoing shared public changes
- `git reset` is best used for undoing local private changes

In addition to the primary undo commands, we took a look at other Git utilities: `git log` for finding lost commits `git clean` for undoing uncommitted changes `git add` for modifying the staging index.

Each of these commands has its own in-depth documentation. To learn more about a specific command mentioned here, visit the corresponding links.



![Rewriting history](https://www.atlassian.com/dam/jcr:8e57216e-269e-49e6-aff2-5c03b8512e73/hero.svg)

##### Next up:

#### Git Clean

START NEXT TUTORIAL