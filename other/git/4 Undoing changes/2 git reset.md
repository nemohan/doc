# git reset

[git checkout](https://www.atlassian.com/git/tutorials/undoing-changes)[git clean](https://www.atlassian.com/git/tutorials/undoing-changes/git-clean)[git revert](https://www.atlassian.com/git/tutorials/undoing-changes/git-revert)[git reset](https://www.atlassian.com/git/tutorials/undoing-changes/git-reset)[git rm](https://www.atlassian.com/git/tutorials/undoing-changes/git-reset)

The `git reset` command is a complex and versatile tool for undoing changes. It has three primary forms of invocation. These forms correspond to command line arguments `--soft, --mixed, --hard`. The three arguments each correspond to Git's three internal state management mechanism's, The Commit Tree (HEAD), The Staging Index, and The Working Directory.

## Git reset & three trees of Git

To properly understand `git reset` usage, we must first understand Git's internal state management systems. Sometimes these mechanisms are called Git's "three trees". Trees may be a misnomer, as they are not strictly traditional tree data-structures. They are, however, node and pointer-based data structures that Git uses to track a timeline of edits. The best way to demonstrate these mechanisms is to create a changeset in a repository and follow it through the three trees.

Ready to learn git reset?

Try this interactive tutorial.

Get started now



![Rewriting history](https://www.atlassian.com/dam/jcr:8e57216e-269e-49e6-aff2-5c03b8512e73/hero.svg)

##### Next up:

#### Git RM

START NEXT TUTORIA