[English](GUIDE.md) · [Deutsch](BEDIENUNGSANLEITUNG.md)

# Anleitung für Vertrauenspersonen

Bewahre deinen Brief verschlossen und getrennt von anderen Briefen auf. Melde ein beschädigtes Siegel beim angegebenen Kontakt. Werkzeuge und Tresorkopien müssen im Notfall auch ohne den Controller erreichbar sein.

1. Prüft gemeinsam den Anlass, den Notfallkontakt, das vorgesehene Konto und die Satz-ID. Alle verwendeten Teile müssen aus demselben Satz und Bereich stammen. Für Master und Infrastruktur können unterschiedliche Schwellen gelten.
2. Folgt auf dem vorbereiteten Rechner dem [Schnellstart](START-HIER.md). Übernehmt jedes Zeichen, auch die Prüfsumme und alle durch `~` getrennten Blöcke. Die Prüfsumme erkennt Übertragungsfehler. Die Herkunft der Briefe prüft ihr gesondert.
3. Wählt **Jetzt anzeigen**, wenn niemand mitliest. Leerzeichen im Passwort gehören dazu. Nutzt für Master das dokumentierte Vaultwarden-Konto und den zugehörigen Server. Einen TOTP-Einrichtungsschlüssel übernehmt ihr in den vertrauenswürdigen Authenticator. Einen Wiederherstellungscode verwendet ihr im vorgesehenen 2FA-Notfallverfahren. Verbrauchte Einmalcodes müssen ersetzt werden.
4. Für den Infrastrukturzugang gelten das eigene Konto und Verfahren aus dem Brief. Eine KDBX-Kopie kann ein eigenes Passwort, eine Schlüsseldatei oder andere Voraussetzungen haben. Prüft diese gesondert.
5. Leert die Anzeige, beendet den Dienst und dokumentiert Teilnehmende und Satz-ID. Teile, Zugangsdaten und Bildschirmfotos gehören weder in Protokolle noch in Chats oder Cloud-Dienste. Veranlasst bei Bedarf neue Zugangsdaten und Briefe.

Ein Doppelklick auf die HTML-Datei zeigt den Startweg. Der lokale Dienst übernimmt die Berechnung. Alternativ fragt `python3 recover.py` die Teile verdeckt im Terminal ab. Erst nach Eingabe von `REVEAL` zeigt es das Ergebnis. Schließt danach das Terminal. Achtet auf Terminalverlauf, Auslagerungsdateien, Druckwarteschlangen und Backups.
