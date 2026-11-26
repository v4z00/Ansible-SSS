[English](README.md) · [Deutsch](README.de.md)

# Ansible-SSS

Give several people a way to recover access together. Each trustee receives a personal letter with one or two shares. A configurable quorum reconstructs the Vaultwarden master password or a separate infrastructure password. The master set can also contain a TOTP setup secret or a 2FA recovery code.

## Set up on Debian

Run the following from the checkout root on the machine that will generate the letters. The staging branch contains the development version.

```bash
git clone --branch staging https://github.com/v4z00/Ansible-SSS.git
cd Ansible-SSS
sudo install -d -m 0700 /root/sss-config
sudo test -e /root/sss-config/config.yml || sudo install -m 0600 examples/config.yml.example /root/sss-config/config.yml
sudo test -e /root/sss-config/trustees.yml || sudo install -m 0600 examples/trustees.yml.example /root/sss-config/trustees.yml
sudoedit /root/sss-config/config.yml /root/sss-config/trustees.yml
```

The two `install -m` commands initialize new files. **On an existing system, keep the private originals.** For a migration, copy the local settings and old `treuhaender.yml` to the two private paths above as root, mode 0600. Existing German field names and installed generator settings are supported. Existing SSS1 and SSS2 letters retain their original threshold.

Enter the real contact, storage locations and conditions for opening the letters. Assign IDs 1 through `shares` exactly once per category. Use `false` for a trustee without a share in that category. The example starts at 2 of 3 in each category. Each accepts 2–20 shares and up to 1,000 possible quorums. Choose `language: en` or `de`, then set `confirmed: true`.

```bash
bash run.sh
bash start-generator.sh --validate
bash start-generator.sh
```

Setup installs Ansible, Python and `ssss` as needed and prepares `/root/rescue/SSS` on this machine. Generation requires a private terminal. Every valid combination is tested before the letters are written. A run creates a new directory under `/root/rescue/SSS/ausgaben`. Each trustee gets only their own letter. Keep other letters, raw output and the generator configuration private. For a one-off language change, use `bash start-generator.sh --lang de`.

## Recover and verify access

Prepare the recovery computer before an emergency. Give trustees the entire `/root/rescue/SSS/offline` folder and access to the documented vault copies. The browser and CLI read the threshold from the first share and verify the set, category and checksum locally. Test master, infrastructure and any separate KDBX access before distribution. A fresh set does not revoke old shares. Rotate the underlying credentials when revocation is required. [Quick start](guides/START-HERE.md) · [Trustee guide](guides/GUIDE.md)

## Optional controller integration

The standalone setup runs independently. On an Ansible-Allgm controller with add-on support, register this repository in the local `versions.txt` as an SSS add-on. Its installer mounts the kit under `playbooks/security/sss` and registers `bin/control sss`. Open `bin/control sss --help` for setup options. Acquire updates with the controller’s update checker. Keep private inputs in `/root/sss-config`.

## Development

Work on `staging`. Enable the Git hooks with `git config core.hooksPath .githooks`. Install Python 3.9+, Node.js for the browser tests, Ansible and the two `ssss` programs. Run:

```bash
python3 -m unittest discover -s tests -v
ansible-playbook -i localhost, --connection local --syntax-check setup.yml
python3 .githooks/staging_manifest.py verify HEAD
```

This project was developed with AI assistance. Reports about unclear instructions and recovery failures are welcome. Please use synthetic data in issues. [MIT license](LICENSE)
