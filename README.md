# TRSModder

This program allows the modding of Dominions 5 TRS files (sprite containers), replacing the standard sprites with others. As far as I can tell, this does not affect multiplayer functionality in any way.
Specifically, this program processes files which instruct it on which sprites to replace with what. The syntax of these mod files (which I arbitrarily gave the .trsm extension) is intended to be simple and remniscent of the standard Dominions .dm files.

This program contains a sample .trsm which prompts for a replacement of each of the magic path icons in turn with their dom4 equivalents.

This program (and .trsm mods) should be played in the data folder of your Dominions directory. Mod files should be placed in subfolders to avoid clutter.

As clearly stated as runtime, this is currently largely untested. **USE AT YOUR OWN RISK**. Currently I have only experimented with modding the following TRS files without issues: build, misc, misc2, res, blast, item

Sprite indexes should be obtained from one of the sprite dumps floating around out there. I am happy to offer further guidance on this if required.

## Thanks

noblesse_oblige, for his work on and scripts for parsing the Dominions type TRS files, without which there is no way I would have done this!