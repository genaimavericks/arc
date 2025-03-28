# SSH Setup for GitHub

This document outlines the steps to set up SSH authentication for GitHub, which is required for accessing private repositories.

## SSH Key Setup Process

### 1. Check for Existing SSH Keys

```bash
ls -la ~/.ssh
```

### 2. Generate a New SSH Key (if needed)

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

When prompted, save the key to the default location or specify a custom path (e.g., `~/.ssh/git_dpk_ssh_key`).

### 3. Set Proper Permissions for Your SSH Key

```bash
chmod 600 ~/.ssh/git_dpk_ssh_key
```

### 4. Create or Update SSH Config File

Create a file at `~/.ssh/config` with the following content:

```
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/git_dpk_ssh_key
  IdentitiesOnly yes
```

### 5. Add Your SSH Key to GitHub

1. Copy your public key to the clipboard:
   ```bash
   cat ~/.ssh/git_dpk_ssh_key.pub
   ```

2. Go to GitHub → Settings → SSH and GPG keys → New SSH key
3. Paste your public key and give it a descriptive title
4. Click "Add SSH key"

### 6. Test Your SSH Connection

```bash
ssh -T git@github.com
```

You should see: "Hi username! You've successfully authenticated, but GitHub does not provide shell access."

## Using SSH with Git

### Clone a Repository

```bash
git clone git@github.com:RSWdjinni/rsw.git
```

### Update Remote URL for Existing Repositories

If you've already cloned a repository using HTTPS, update it to use SSH:

```bash
git remote set-url origin git@github.com:RSWdjinni/rsw.git
```

### Verify Remote URL

```bash
git remote -v
```

## Troubleshooting

If you encounter "Permission denied (publickey)" errors:
1. Verify your SSH key is added to GitHub
2. Check that your SSH config is correctly set up
3. Ensure your key has the correct permissions (600)
4. Try adding your key to the SSH agent:
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/git_dpk_ssh_key
   ```

## References

- [GitHub Docs: Connecting to GitHub with SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
