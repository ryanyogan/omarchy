echo "Give Dropbox a shared lifecycle owner and reload user shutdown settings"

systemctl --user daemon-reload
if omarchy-cmd-present dropbox-cli; then
  omarchy-setup-dropbox --migrate
fi
systemctl --user daemon-reexec
