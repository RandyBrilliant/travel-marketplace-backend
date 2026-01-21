# GitHub Actions CI/CD Deployment Guide

This guide explains how to set up automatic deployment to your DigitalOcean droplet using GitHub Actions.

## Overview

The GitHub Actions workflow automatically:
1. Triggers when you push to the `main` branch
2. SSHs into your DigitalOcean droplet
3. Pulls the latest code
4. Runs the automated update script
5. Rebuilds and restarts your services

## Setup Instructions

### Step 1: Configure GitHub Secrets

Go to your GitHub repository:
```
Settings → Secrets and variables → Actions → New repository secret
```

Add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DO_HOST` | Your droplet's IP address | `165.232.123.45` |
| `DO_USERNAME` | SSH username | `root` or your user |
| `DO_SSH_PRIVATE_KEY` | Your SSH private key (see below) | Full private key content |
| `DO_SSH_PORT` | SSH port | `22` |
| `DO_PROJECT_PATH` | Full path to backend project on droplet | `/root/travel-marketplace-backend` |

### Step 2: Get Your SSH Private Key

#### Option A: Use Existing Key

On your local machine:
```bash
cat ~/.ssh/id_rsa
```

Copy the **entire output** including:
- `-----BEGIN OPENSSH PRIVATE KEY-----`
- All the content in between
- `-----END OPENSSH PRIVATE KEY-----`

Paste it into the `DO_SSH_PRIVATE_KEY` secret.

#### Option B: Create Dedicated Deploy Key (Recommended)

1. Generate a new SSH key:
```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy
```

2. Copy the public key to your droplet:
```bash
ssh-copy-id -i ~/.ssh/github_deploy.pub your_user@your_droplet_ip
```

Or manually:
```bash
# Display public key
cat ~/.ssh/github_deploy.pub

# SSH to droplet and add to authorized_keys
ssh your_user@your_droplet_ip
mkdir -p ~/.ssh
echo "paste_public_key_here" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

3. Get the private key for GitHub:
```bash
cat ~/.ssh/github_deploy
```

### Step 3: Verify Droplet Setup

On your DigitalOcean droplet, ensure:

1. Git is installed:
```bash
git --version
```

2. Docker and Docker Compose are installed:
```bash
docker --version
docker compose version
```

3. Your backend project is cloned and in the correct location:
```bash
cd /root/travel-marketplace-backend  # or your project path
git status
```

### Step 4: Commit and Push Workflow

```bash
# Add the workflow file
git add .github/workflows/deploy.yml

# Add the automated update script
git add deploy/update-auto.sh

# Commit
git commit -m "Add GitHub Actions deployment workflow"

# Push to trigger deployment
git push origin main
```

## Testing the Workflow

### Monitor Deployment

1. Go to your GitHub repository
2. Click on **Actions** tab
3. You'll see your workflow running
4. Click on it to see detailed logs

### Manual Trigger

You can also manually trigger the deployment:
1. Go to **Actions** tab
2. Click on "Deploy to DigitalOcean" workflow
3. Click "Run workflow"
4. Select the branch and click "Run workflow"

## Troubleshooting

### SSH Connection Fails

**Issue:** `Permission denied (publickey)`

**Solution:**
1. Verify the private key is correct in GitHub secrets
2. Check that the public key is in `~/.ssh/authorized_keys` on the droplet
3. Verify SSH port is correct (usually 22)

### Git Pull Fails

**Issue:** `fatal: could not read Username`

**Solution:** On your droplet, ensure the repository is using HTTPS or SSH properly:
```bash
cd /root/travel-marketplace-backend
git remote -v
# If using HTTPS, it should show: https://github.com/yourusername/yourrepo.git
# If using SSH, it should show: git@github.com:yourusername/yourrepo.git
```

For HTTPS, you may need to configure credentials on the droplet.

### Docker Permission Issues

**Issue:** `Got permission denied while trying to connect to the Docker daemon socket`

**Solution:**
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Or run with sudo
# Modify the workflow to use sudo in the script
```

### Port Already in Use

**Issue:** Service fails to start because port is already in use

**Solution:** The `update-auto.sh` script stops services first, but if needed:
```bash
docker compose -f docker-compose.prod.yml down
docker ps -a  # Check for any lingering containers
docker rm -f $(docker ps -aq)  # Remove all containers if needed
```

## Advanced Configuration

### Run Tests Before Deploy

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run Tests
        run: |
          python manage.py test
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    # ... rest of deploy job
```

### Add Slack/Discord Notifications

```yaml
- name: Notify Deployment Success
  if: success()
  uses: slackapi/slack-github-action@v1.25.0
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "✅ Backend deployment successful!"
      }
```

### Deploy Only on Specific File Changes

```yaml
on:
  push:
    branches:
      - main
    paths:
      - '**.py'
      - 'requirements.txt'
      - 'docker-compose.prod.yml'
      - 'Dockerfile.prod'
```

## Security Best Practices

1. **Use Dedicated Deploy Keys:** Don't use your personal SSH key
2. **Limit Key Permissions:** Create a deploy user with limited sudo access
3. **Enable 2FA:** Use GitHub's two-factor authentication
4. **Rotate Keys:** Regularly update SSH keys
5. **Monitor Deployments:** Review deployment logs regularly

## Files Created

- `.github/workflows/deploy.yml` - GitHub Actions workflow
- `deploy/update-auto.sh` - Non-interactive update script

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [SSH Action Documentation](https://github.com/appleboy/ssh-action)
- [DigitalOcean Deployment Guide](https://docs.digitalocean.com/)
