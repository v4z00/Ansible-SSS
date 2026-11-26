[English](GUIDE.md) · [Deutsch](BEDIENUNGSANLEITUNG.md)

# Trustee guide

Keep your personal letter sealed. Store it separately from other trustees’ letters. If the seal is broken, contact the person named in the letter. Keep the offline tools and vault copies accessible when the controller is unavailable.

1. Check the reason for opening the letters, the emergency contact, the intended account and the set ID. All shares must come from the same set and category. The master and infrastructure sets have independent thresholds.
2. On the prepared recovery computer, follow [Start here](START-HERE.md). Enter every character, including the checksum and any blocks separated by `~`. A checksum detects transcription errors. Verify the origin of each letter separately.
3. Choose **Reveal for this session** when nobody else can read the screen. Preserve spaces in the password. For master access use the documented Vaultwarden account and server. Import a recovered TOTP setup secret into its trusted authenticator, or use the recovery code in the documented 2FA procedure. A used single-use code needs replacement.
4. For infrastructure access, use the separate account and procedure in the letter. A KDBX copy can have its own password, key file or other requirements. Check these separately.
5. Clear the result, close the service and record who participated and which set was used. Keep shares, credentials and screenshots out of logs, chat and cloud tools. Arrange credential rotation and new letters when required.

Opening the HTML file directly displays launch instructions. The launcher runs the calculation on the same computer. The CLI alternative `python3 recover.py` asks for shares without echo and reveals the credentials only after you type `REVEAL`. Close the terminal when you finish. On a shared computer, account for terminal scrollback, swap, print queues and backups.
