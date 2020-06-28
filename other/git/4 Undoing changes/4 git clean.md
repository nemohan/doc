# git clean

[TOC]

git clean 用于删除未被跟踪的文件

[git checkout](https://www.atlassian.com/git/tutorials/undoing-changes)[git clean](https://www.atlassian.com/git/tutorials/undoing-changes/git-clean)[git revert](https://www.atlassian.com/git/tutorials/undoing-changes/git-revert)[git reset](https://www.atlassian.com/git/tutorials/undoing-changes/git-reset)[git rm](https://www.atlassian.com/git/tutorials/undoing-changes/git-rm)

In this section, we will focus on a detailed discussion of the `git clean` command. `Git clean` is to some extent an 'undo' command. `Git clean` can be considered complementary to other commands like `git reset` and `git checkout`. Whereas these other commands operate on files previously added to the Git tracking index, <font color="red">the `git clean` command operates on untracked files. Untracked files are files that have been created within your repo's working directory but have not yet been added to the repository's tracking index using the `git add` command. To better demonstrate the difference between tracked and untracked files consider the following command line example:</font>

```bash
$ mkdir git_clean_test
$ cd git_clean_test/
$ git init .
Initialized empty Git repository in /Users/kev/code/git_clean_test/.git/

$ echo "tracked" > ./tracked_file

$ git add ./tracked_file

$ echo "untracked" > ./untracked_file

$ mkdir ./untracked_dir && touch ./untracked_dir/file
$ git status
On branch master

Initial commit

Changes to be committed: (use "git rm --cached <file>..." to unstage)

new file: tracked_file

Untracked files: (use "git add <file>..." to include in what will be committed) untracked_dir/ untracked_file
```

The example creates a new Git repository in the `git_clean_test` directory. It then proceeds to create a `tracked_file` which is added to the Git index, additionally, an `untracked_file` is created, and an `untracked_dir`. The example then invokes `git status` which displays output indicating Git's internal state of tracked and untracked changes. With the repository in this state, we can execute the `git clean` command to demonstrate its intended purpose.

```
$ git clean fatal: clean.requireForce defaults to true and neither -i, -n, nor -f given; refusing to clean
```

At this point, executing the default `git clean` command may produce a fatal error. The example above demonstrates what this may look like. By default, Git is globally configured to require that `git clean` be passed a "force" option to initiate. This is an important safety mechanism. When finally executed `git clean` is not undo-able. When fully executed, `git clean` will make a hard filesystem deletion, similar to executing the command line rm utility. Make sure you really want to delete the untracked files before you run it.

## Common options and usage

Given the previous explanation of the default `git clean` behaviors and caveats, the following content demonstrates various `git clean` use cases and the accompanying command line options required for their operation.

```
-n
```

<font color="red">The `-n` option will perform a “dry run” of `git clean`. This will show you which files are going to be removed without actually removing them. It is a best practice to always first perform a dry run of `git clean`. We can demonstrate this option in the demo repo we created earlier.</font>

```
$ git clean -n
Would remove untracked_file
```

The output tells us that `untracked_file` will be removed when the `git clean` command is executed. Notice that the `untracked_dir` is not reported in the output here. By default `git clean` will not operate recursively on directories. This is another safety mechanism to prevent accidental permanent deletion.

```
-f or --force
```

The force option initiates the actual deletion of untracked files from the current directory. Force is required unless the `clean.requireForce` configuration option is set to false. This will not remove untracked folders or files specified by `.gitignore`. Let us now execute a live `git clean` in our example repo.

```
$ git clean -f
Removing untracked_file
```

The command will output the files that are removed. You can see here that `untracked_file` has been removed. Executing `git status` at this point or doing a `ls` will show that `untracked_file` has been deleted and is nowhere to be found. By default `git clean -f` will operate on all the current directory untracked files. Additionally, a <path> value can be passed with the `-f` option that will remove a specific file.

```
git clean -f <path>
-d include directories
```

The `-d` option tells `git clean` that you also want to remove any untracked directories, by default it will ignore directories. We can add the `-d` option to our previous examples:

```
$ git clean -dn
Would remove untracked_dir/
$ git clean -df
Removing untracked_dir/
```

Here we have executed a 'dry run' using the `-dn` combination which outputs `untracked_dir` is up for removal. Then we execute a forced clean, and receive output that `untracked_dir` is removed.

```
-x force removal of ignored files
```

A common software release pattern is to have a build or distribution directory that is not committed to the repositories tracking index. The build directory will contain ephemeral build artifacts that are generated from the committed source code. This build directory is usually added to the repositories `.gitignore` file. It can be convenient to also clean this directory with other untracked files. The `-x` option tells `git clean` to also include any ignored files. As with previous `git clean` invocations, it is a best practice to execute a 'dry run' first, before the final deletion. The `-x` option will act on all ignored files, not just project build specific ones. This could be unintended things like ./.idea IDE configuration files.

```
git clean -xf
```

Like the `-d` option `-x` can be passed and composed with other options. This example demonstrates a combination with `-f` that will remove untracked files from the current directory as well as any files that Git usually ignores.

## Interactive mode or git clean interactive

In addition to the ad-hoc command line execution we have demonstrated so far, `git clean` has an "interactive" mode that you can initiate by passing the `-i` option. Let us revisit the example repo from the introduction of this document. In that initial state, we will start an interactive clean session.

```
$ git clean -di
Would remove the following items:
 untracked_dir/ untracked_file
*** Commands ***
 1: clean 2: filter by pattern 3: select by numbers 4: ask each 5: quit 6: help
What now>
```

We have initiated the interactive session with the `-d` option so it will also act upon our `untracked_dir`. The interactive mode will display a `What now>` prompt that requests a command to apply to the untracked files. The commands themselves are fairly self explanatory. We'll take a brief look at each in a random order starting with command `6: help`. Selecting command 6 will further explain the other commands:

```
What now> 6
clean - start cleaning
filter by pattern - exclude items from deletion
select by numbers - select items to be deleted by numbers
ask each - confirm each deletion (like "rm -i")
quit - stop cleaning
help - this screen
? - help for prompt selection
5: quit
```

Is straight forward and will exit the interactive session.

```
1: clean
```

Will delete the indicated items. If we were to execute `1: clean` at this point `untracked_dir/ untracked_file` would be removed.

```
4: ask each
```

will iterate over each untracked file and display a `Y/N` prompt for a deletion. It looks like the following:

```
*** Commands ***
 1: clean 2: filter by pattern 3: select by numbers 4: ask each 5: quit 6: help
What now> 4
Remove untracked_dir/ [y/N]? N
Remove untracked_file [y/N]? N
2: filter by pattern
```

Will display an additional prompt that takes input used to filter the list of untracked files.

```
Would remove the following items:
 untracked_dir/ untracked_file
*** Commands ***
 1: clean 2: filter by pattern 3: select by numbers 4: ask each 5: quit 6: help
What now> 2
 untracked_dir/ untracked_file
Input ignore patterns>> *_file
 untracked_dir/
```

Here we input the `*_file` wildcard pattern which then restricts the untracked file list to just `untracked_dir`.

```
3: select by numbers
```

Similar to command 2, command 3 works to refine the list of untracked file names. The interactive session will prompt for numbers that correspond to an untracked file name.

```
Would remove the following items:
 untracked_dir/ untracked_file
*** Commands ***
 1: clean 2: filter by pattern 3: select by numbers 4: ask each 5: quit 6: help
What now> 3
 1: untracked_dir/ 2: untracked_file
Select items to delete>> 2
 1: untracked_dir/ * 2: untracked_file
Select items to delete>>
Would remove the following item:
 untracked_file
*** Commands ***
 1: clean 2: filter by pattern 3: select by numbers 4: ask each 5: quit 6: help
```

## Summary

To recap, `git clean` is a convenience method for deleting untracked files in a repo's working directory. Untracked files are those that are in the repo's directory but have not yet been added to the repo's index with `git add`. Overall the effect of `git clean` can be accomplished using `git status` and the operating systems native deletion tools. `Git clean` can be used alongside `git reset` to fully undo any additions and commits in a repository.



![Rewriting history](https://www.atlassian.com/dam/jcr:8e57216e-269e-49e6-aff2-5c03b8512e73/hero.svg)

##### Next up:

#### Git Revert

START NEXT TUTORIAL