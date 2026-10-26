"""The crowned Birthday Person's clips: `clips_birthday.build` against `birthday.CROWN`."""
import birthday
from clips_birthday import build, feet

C = birthday.CROWN
FEET = feet(C)
CLIPS = build(C)


if __name__ == "__main__":
    for clip in CLIPS.values():
        print(clip.summary())
