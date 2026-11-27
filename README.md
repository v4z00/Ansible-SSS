[English](README.md) · [Deutsch](README.de.md)

# Ansible-SSS

Give several people a way to recover access together. Each trustee receives a personal letter with one or two shares. A configurable quorum reconstructs the Vaultwarden master password or a separate infrastructure password. The master set can also contain a TOTP setup secret or a 2FA recovery code.

## What a recovery looks like

With the example 2-of-3 quorum, any two appointed trustees can bring their letters to an offline computer. They open the recovery page, choose the same category and enter one share from each letter. The tool checks that the shares belong to the same set and verifies the recovered value. A trustee holding only one share cannot complete this example alone.

The [quick start](guides/START-HERE.md) is for the people opening the letters. The [trustee guide](guides/GUIDE.md) covers checking the result and using the recovery material. The administrator uses [examples/](examples/) to define the quorum and letter recipients before distribution.

**Staging s0.1.2** adds this walkthrough. Existing letters and recovery kits can be used as before.

## Set up on Debian

Clone the stable release on the machine that will generate the letters.

```bash
git clone --branch main https://github.com/v4z00/Ansible-SSS.git
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

On a controller with Allgm 0.8.1 or later, add these two lines to the existing local `versions.txt`. Keep the other module rows and the empty final token field.

```text
# addon=SSS
SSS|0.0.0|https://github.com/v4z00/Ansible-SSS.git|
```

From the controller directory, preview the stable update, review all changes, then apply it:

```bash
bin/control update-check --remote
bin/control update-check --apply
bin/control module-versions
bin/control sss --help
```

The update covers all registered modules and installs the kit under `playbooks/security/sss`. The registered command provides setup options. Producing letters remains an explicit local step. Keep private inputs under `/root/sss-config`. The standalone workflow above also works without a controller.

## Development

Work on `staging`. Enable the Git hooks with `git config core.hooksPath .githooks`. Install Python 3.9+, Node.js for the browser tests, Ansible and the two `ssss` programs. Run:

```bash
python3 -m unittest discover -s tests -v
ansible-playbook -i localhost, --connection local --syntax-check setup.yml
python3 .githooks/staging_manifest.py verify HEAD
```

This project was developed with AI assistance. Reports about unclear instructions and recovery failures are welcome. Please use synthetic data in issues. [MIT license](LICENSE)
