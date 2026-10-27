VincentVoice_P - Vincent's own voice in Cloud's slot (Create a Character System, Vincent mod)

Cloud's three battle voice banks (VO_PC0000_00_Cloud, VO_PC0000_01_Cloud_Past, VO_PC0000_02_Cloud_Insanity, English) with
the moments below given Vincent's own lines from the game; everything else Cloud said in battle and in the field
(grunts, attack and ability callouts, banter, climbing and landing efforts) is silent.

  battle start      Let's go. / Hope you're ready for a fight. / A duel it is. / Be brief. / We'll soon find out. /
                    Gotta do my job sometime.   (bosses: Who dares disturb my slumber?)
  enemy staggered   Hmph... Scared?
  enemy down        Had enough, then?          finishing blow: Hmph.
  limit break       Get out... Now. / Then I've one more sin to atone for.
  summon            Come.
  switched to him   Well? / Need something? / Loud and clear.     (in a crisis: You having trouble?)
  healed            Even better.
  knocked out       Let me sleep.              revived: Just resting my eyes.
  victory           Hmph. / Diverting, if nothing else. / I'd hoped for a better match than that. /
                    All's well that ends well, I suppose.
  victory, ally down  Couldn't have you dying on me just yet. / You are not to blame for this.
  game over         Expectations often lead to disappointment.

Only the English voice: with the Japanese, French or German voice Cloud's own voice stays. Story scenes and field
conversations keep their lines (those are not this bank).
To remove: delete VincentVoice_P.pak, .utoc and .ucas from Paks\~mods.

v2 (2026-10-16): fixes v1's crash at start-up, "This platform requires cooked packages, and audio data was not cooked
into SQEXSEADSound /Game/Sound/Voice/JP/Character/Player/VO_PC0000_00_Cloud". A bank keeps its size in three places
(AudioMog's repacker updates the same three); v1 updated two, so the game read the bank's last bytes from the wrong
place. The game loads the English bank under the Japanese name (its voice language system), which is why the message
names JP. v2 also gives the banks the game's own container entries (16-byte export alignment, load order).
