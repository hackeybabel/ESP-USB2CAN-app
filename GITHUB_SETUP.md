# GitHub repo setup

The project is already a Git repo with an initial commit pending. Follow these steps to publish it on GitHub.

## 1. Set your Git identity (once per machine)

If you haven’t already:

```powershell
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

Use the same email as your GitHub account if you want commits linked to your profile.

## 2. Create the initial commit

```powershell
cd "e:\new_stuff\ESP-USB2CAN-app"
git commit -m "Initial commit: ESP-USB2CAN GUI app"
```

## 3. Create the repository on GitHub

1. Open https://github.com/new
2. **Repository name:** `ESP-USB2CAN-app` (or any name you prefer)
3. **Description (optional):** e.g. “Cross-platform GUI for ESP USB to CAN (ESP32-C3) bridge”
4. Choose **Public** (or Private)
5. **Do not** add a README, .gitignore, or license (this project already has them)
6. Click **Create repository**

## 4. Connect and push

GitHub will show commands; use these (replace `YOUR_USERNAME` with your GitHub username):

```powershell
cd "e:\new_stuff\ESP-USB2CAN-app"
git remote add origin https://github.com/YOUR_USERNAME/ESP-USB2CAN-app.git
git branch -M main
git push -u origin main
```

If you use SSH:

```powershell
git remote add origin git@github.com:YOUR_USERNAME/ESP-USB2CAN-app.git
git branch -M main
git push -u origin main
```

After this, your code will be on GitHub. You can delete this file (`GITHUB_SETUP.md`) once you’re done, or keep it for reference.
