# git rm

[TOC]

<font color="red">A common question when getting started with Git is "How do I tell Git not to track a file (or files) any more?" The `git rm` command is used to remove files from a Git repository. It can be thought of as the inverse of the `git add` command.</font>


git rm 相当于rm 命令和git add 的结合体，即首先执行rm删除文件，再执行git add 添加到暂存区。但略有区别即git rm 有安全性检查

## Git rm Overview

The `git rm` command can be used to remove individual files or a collection of files. The primary function of `git rm` is to remove tracked files from the Git index. Additionally, `git rm` can be used to remove files from both the staging index and the working directory. There is no option to remove a file from only the working directory.<font color="red"> The files being operated on must be identical to the files in the current `HEAD`. If there is a discrepancy between the `HEAD` version of a file and the staging index or working tree version, Git will block the removal. This block is a safety mechanism to prevent removal of in-progress changes.(被删除的文件x必须和HEAD指向的历史版本保持一致，若不一致，文件x有改动，已放入暂存区或不在暂存区，此时使用git rm 删除x 会被阻止并提示</font>

Note that `git rm` does not remove branches. Learn more about [using git branches](https://www.atlassian.com/git/tutorials/using-branches)

## Usage

Specifies the target files to remove. The option value can be an individual file, a space delimited list of files `file1 file2 file3`, or a wildcard file glob `(~./directory/*)`.

```bash
-f
--force
```

**The `-f`option is used to override the safety check that Git makes to ensure that the files in `HEAD` match the current content in the staging index and working director**y.



```
-n
--dry-run
```

<font color="red">The "dry run" option is a safeguard that will execute the `git rm`command but not  actually delete the files. Instead it will output which files it would have removed.</font>



```
-r
```

The `-r` option is shorthand for 'recursive'. When operating in recursive mode `git rm` will remove a target directory and all the contents of that directory.

```bash
--
```

The separator option is used to explicitly distinguish between a list of file names and the arguments being passed to `git rm`. This is useful if some of the file names have syntax that might be mistaken for other options.

```
--cached
```

**The cached option specifies that the removal should happen only on the staging index. Working directory files will be left alone.**  这有什么用，相当于没有删除文件

```
--ignore-unmatch
```

This causes the command to exit with a 0 sigterm status even if no files matched. This is a Unix level status code. The code 0 indicates a successful invocation of the command. The `--ignore-unmatch` option can be helpful when using `git rm` as part of a greater shell script that needs to fail gracefully.

```
-q
--quiet
```

The quiet option hides the output of the `git rm` command. The command normally outputs one line for each file removed.

## How to undo git rm

Executing `git rm` is not a permanent update. The command will update the staging index and the working directory. These changes will not be persisted until a new commit is created and the changes are added to the commit history. This means that the changes here can be "undone" using common Git commands.

```
git reset HEAD 执行这条命令相当于使用--mixed方式，更新staging index, 将被删除的文件从暂存区移出，但工作目录中仍然没有被删除文件。应该使用git reset --hard
```

A reset will revert the current staging index and working directory back to the `HEAD` commit. This will undo a `git rm`. 

```bash
git checkout .
```

A checkout will have the same effect and restore the latest version of a file from `HEAD`.

In the event that `git rm` was executed and a new commit was created which persist the removal, `git reflog` can be used to find a ref that is before the `git rm` execution. Learn more about [using git reflog](https://www.atlassian.com/git/tutorials/rewriting-history/git-reflog).

## Discussion

The <`file>` argument given to the command can be exact paths, wildcard file glob patterns, or exact directory names. The command removes only paths currently commited to the Git repository.

Wildcard file globbing matches across directories. It is important to be cautious when using wildcard globs. Consider the examples: `directory/*` and `directory*`. The first example will remove all sub files of `directory/` whereas the second example will remove all sibling directories like `directory1``directory2``directory_whatever` which may be an unexpected result.

## <font color="red">The scope of git rm</font>

The `git rm` command operates on the current branch only. The removal event is only applied to the working directory and staging index trees. The file removal is not persisted to the repository history until a new commit is created.

## Why use git rm instead of rm

<font color="green">A Git repository will recognize when a regular shell `rm` command has been executed on a file it is tracking. It will update the working directory to reflect the removal. It will not update the staging index with the removal. An additional `git add` command will have to be executed on the removed file paths to add the changes to the staging index. The `git rm` command acts a shortcut in that it will update the working directory and the staging index with the removal.</font>

## Examples

```
git rm Documentation/\*.txt
```

This example uses a wildcard file glob to remove all `*.txt files` that are children of the `Documentation` directory and any of its subdirectories.

Note that the asterisk * is escaped with slashes in this example; this is a guard that prevents the shell from expanding the wildcard. The wildcard then expands the pathnames of files and subdirectories under the `Documentation/` directory.

```
git rm -f git-*.sh
```

This example uses the force option and targets all wildcard `git-*.sh` files. The force option explicitly removes the target files from both the working directory and staging index.

## How to remove files no longer in the filesystem

As stated above in "Why use `git rm` instead of `rm`" , `git rm` is actually a convenience command that combines the standard shell `rm` and `git add` to remove a file from the working directory and promote that removal to the staging index. A repository can get into a cumbersome state in the event that several files have been removed using only the standard shell `rm` command.

If intentions are to record all the explicitly removed files as part of the next commit, `git commit -a` will add all the removal events to the staging index in preparation of the next commit.

If however, intentions are to persistently remove the files that were removed with the shell `rm`, use the following command:

```
git diff --name-only --diff-filter=D -z | xargs -0 git rm --cached
```

This command will generate a list of the removed files from the working directory and pipe that list to `git rm --cached` which will update the staging index.

## Git rm summary

`git rm` is a command that operates on two of the primary Git [internal state management trees](https://www.atlassian.com/git/tutorials/undoing-changes/git-reset): the working directory, and staging index. `git rm` is used to remove a file from a Git repository. It is a convenience method that combines the effect of the default shell `rm` command with `git add`. This means that it will first remove a target from the filesystem and then add that removal event to the staging index. The command is one of many that can be used for [undoing changes in Git.](https://www.atlassian.com/git/tutorials/undoing-changes)