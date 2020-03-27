# What is an SSH KEY?

 

An SSH key is an access credential for the SSH (secure shell) network protocol. This authenticated and encrypted secure network protocol is used for remote communication between machines on an [unsecured open network](https://whatismyipaddress.com/unsecured-network). SSH is used for remote file transfer, network management, and remote operating system access. The SSH acronym is also used to describe a set of tools used to interact with the SSH protocol.

SSH uses a pair of keys to initiate a secure handshake between remote parties. The key pair contains a public and private key. The private vs public nomenclature can be confusing as they are both called keys. It is more helpful to think of the public key as a "lock" and the private key as the "key". You give the public 'lock' to remote parties to encrypt or 'lock' data. This data is then opened with the 'private' key which you hold in a secure place.

## How to Create an SSH Key

SSH keys are generated through a [public key cryptographic algorithm](https://en.wikipedia.org/wiki/Public-key_cryptography), the most common being [RSA](https://en.wikipedia.org/wiki/RSA_(cryptosystem)) or [DSA](https://en.wikipedia.org/wiki/Digital_Signature_Algorithm). At a very high level SSH keys are generated through a mathematical formula that takes 2 prime numbers and a random seed variable to output the public and private key. This is a one-way formula that ensures the public key can be derived from the private key but the private key cannot be derived from the public key.

SSH keys are created using a key generation tool. The SSH command line tool suite includes a keygen tool. Most git hosting providers offer guides on [how to create an SSH Key.](https://confluence.atlassian.com/bitbucketserver/creating-ssh-keys-776639788.html)

~~~
alias config='/usr/bin/git --git-dir=$HOME/.cfg/ --work-tree=$HOME'
~~~



Both OsX and Linux operating systems have comprehensive modern terminal applications that ship with the SSH suite installed. The process for creating an SSH key is the same between them.

\1. execute the following to begin the key creation

```
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

This command will create a new SSH key using the email as a label

\2. You will then be prompted to "Enter a file in which to save the key."
You can specify a file location or press “Enter” to accept the default file location.

```
> Enter a file in which to save the key (/Users/you/.ssh/id_rsa): [Press enter]
```

\3. The next prompt will ask for a secure passphrase.
A passphrase will add an additional layer of security to the SSH and will be required anytime the SSH key is used. If someone gains access to the computer that private keys are stored on, they could also gain access to any system that uses that key. Adding a passphrase to keys will prevent this scenario.

```
> Enter passphrase (empty for no passphrase): [Type a passphrase]
> Enter same passphrase again: [Type passphrase again]
```

At this point, a new SSH key will have been generated at the previously specified file path.

\4. Add the new SSH key to the ssh-agent

The ssh-agent is another program that is part of the SSH toolsuite. The ssh-agent is responsible for holding private keys. Think of it like a keychain. In addition to holding private keys it also brokers requests to sign SSH requests with the private keys so that private keys are never passed around unsecurly.

Before adding the new SSH key to the ssh-agent first ensure the ssh-agent is running by executing:

```
$ eval "$(ssh-agent -s)"
> Agent pid 59566
```

Once the ssh-agent is running the following command will add the new SSH key to the local SSH agent.

```
ssh-add -K /Users/you/.ssh/id_rsa
```

The new SSH key is now registered and ready to use!

~~~
curl -Lks http://bit.do/cfg-init | /bin/bash
~~~



Windows environments do not have a standard default unix shell. External shell programs will need to be installed for to have a complete keygen experience. The most straight forward option is to utilize [Git Bash](https://www.atlassian.com/git/tutorials/git-bash). Once Git Bash is installed the same steps for Linux and Mac can be followed within the Git Bash shell.

~~~
git init --bare $HOME/.cfg alias config='/usr/bin/git --git-dir=$HOME/.cfg/ --work-tree=$HOME' config config --local status.showUntrackedFiles no echo "alias config='/usr/bin/git --git-dir=$HOME/.cfg/ --work-tree=$HOME'" >> $HOME/.bashrc
~~~



Modern windows environments offer a windows linux subsystem. The windows linux subsystem offers a full linux shell within a traditional windows environment. If a linux subsystem is available the same steps previously discussed for Linux and Mac can be followed with in the windows linux subsystem.

~~~
config status config add .vimrc config commit -m "Add vimrc" config add .bashrc config commit -m "Add bashrc" config push
~~~



SSH keys are used to authenticate secure connections. Following this guide, you will be able to create and start using an SSH key. Git is capable of using SSH keys instead of traditional  password authentication when pushing or pulling to remote repositories. Modern hosted git solutions like [Bitbucket support SSH key authentication.](https://confluence.atlassian.com/bitbucket/set-up-an-ssh-key-728138079.html)