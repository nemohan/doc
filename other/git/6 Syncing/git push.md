# git push

# git push

[git remote](https://www.atlassian.com/git/tutorials/syncing)[git fetch](https://www.atlassian.com/git/tutorials/syncing/git-fetch)[git push](https://www.atlassian.com/git/tutorials/syncing/git-push)[git pull](https://www.atlassian.com/git/tutorials/syncing/git-pull)

The `git push` command is used to upload local repository content to a remote repository. Pushing is how you transfer commits from your local repository to a remote repo. It's the counterpart to `git fetch`, but whereas fetching imports commits to local branches, pushing exports commits to remote branches. Remote branches are configured using the `git remote` command. Pushing has the potential to overwrite changes, caution should be taken when pushing. These issues are discussed below.

## Git push usage

```
git push  
```

Push the specified branch to <remote>, along with all of the necessary commits and internal objects. This creates a local branch in the destination repository. To prevent you from overwriting commits, Git won’t let you push when it results in a non-fast-forward merge in the destination repository.

```
git push  --force
```

Same as the above command, but force the push even if it results in a non-fast-forward merge. Do not use the `--force` flag unless you’re absolutely sure you know what you’re doing.

```
git push  --all
```

Push all of your local branches to the specified remote.

```
git push  --tags
```

Tags are not automatically pushed when you push a branch or use the `--all` option. The `--tags` flag sends all of your local tags to the remote repository.

## Git push discussion

`git push` is most commonly used to publish an upload local changes to a central repository. After a local repository has been modified a push is executed to share the modifications with remote team members.



The above diagram shows what happens when your local `master` has progressed past the central repository’s `master` and you publish changes by running `git push origin master`. Notice how `git push` is essentially the same as running `git merge master` from inside the remote repository.

## Git push and syncing

`git push` is one component of many used in the overall Git "syncing" process. The syncing commands operate on remote branches which are configured using the `git remote` command. `git push` can be considered and 'upload' command whereas, `git fetch` and `git pull` can be thought of as 'download' commands. Once changesets have been moved via a download or upload a `git merge` may be performed at the destination to integrate the changes.

## Pushing to bare repositories

A frequently used, modern Git practice is to have a remotely hosted `--bare` repository act as a central origin repository. This origin repository is often hosted off-site with a trusted 3rd party like Bitbucket. Since pushing messes with the remote branch structure, It is safest and most common to push to repositories that have been created with the `--bare` flag. Bare repos don’t have a working directory so a push will not alter any in progress working directory content. For more information on bare repository creation, read about `git init`.

## Force Pushing

Git prevents you from overwriting the central repository’s history by refusing push requests when they result in a non-fast-forward merge. So, if the remote history has diverged from your history, you need to pull the remote branch and merge it into your local one, then try pushing again. This is similar to how SVN makes you synchronize with the central repository via `svn update` before committing a changeset.

The `--force` flag overrides this behavior and makes the remote repository’s branch match your local one, deleting any upstream changes that may have occurred since you last pulled. The only time you should ever need to force push is when you realize that the commits you just shared were not quite right and you fixed them with a `git commit --amend` or an interactive rebase. However, you must be absolutely certain that none of your teammates have pulled those commits before using the `--force` option.

## Examples

## Default git push

The following example describes one of the standard methods for publishing local contributions to the central repository. First, it makes sure your local master is up-to-date by fetching the central repository’s copy and rebasing your changes on top of them. The interactive rebase is also a good opportunity to clean up your commits before sharing them. Then, the `git push` command sends all of the commits on your local master to the central repository.

```
git checkout master
git fetch origin master
git rebase -i origin/master
# Squash commits, fix up commit messages etc.
git push origin master
```

Since we already made sure the local master was up-to-date, this should result in a fast-forward merge, and `git push` should not complain about any of the non-fast-forward issues discussed above.

## Amended force push

The `git commit` command accepts a `--amend` option which will update the previous commit. A commit is often amended to update the commit message or add new changes. Once a commit is amended a `git push` will fail because Git will see the amended commit and the remote commit as diverged content. The `--force` option must be used to push an amended commit.

```
# make changes to a repo and git add
git commit --amend
# update the existing commit message
git push --force origin master
```

The above example assumes it is being executed on an existing repository with a commit history. `git commit --amend` is used to update the previous commit. The amended commit is then force pushed using the `--force` option.

## Deleting a remote branch or tag

Sometimes branches need to be cleaned up for book keeping or organizational purposes. The fully delete a branch, it must be deleted locally and also remotely.

```
git branch -D branch_name
git push origin :branch_name
```

The above will delete the remote branch named branch_name passing a branch name prefixed with a colon to `git push` will delete the remote branch.



![Making a pull request](https://www.atlassian.com/dam/jcr:d7da7d4a-f994-4c24-90c7-3a5fa7a522aa/hero.svg)

##### Next up:

#### git pull

START NEXT TUTORIAL