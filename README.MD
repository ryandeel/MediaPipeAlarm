# Resisting Alarm Clock

An alarm clock that won't turn off until you get out of bed and move. When the alarm goes off, your webcam turns on and you have to complete a physical challenge (hold a pose or do jumping jacks). MediaPipe tracks your body through the camera and the alarm only stops once you've done it.

CSC 4240 final project by Ryan Deel, AJ Wood, Garrett Nance, Avery Abad, and Derek Nelson.

## Requirements
- **Windows** (the alarm sound uses Python's built-in `winsound`, which is Windows-only)
- A webcam
- Python 3.11 to 3.14

## Setup
Run these from the project folder.

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install the dependencies:
   ```
   pip install -r dependencies.txt
   ```

## Running it
```
python src/alarm_app.py <time>
```

`<time>` can be any of these:

| You type | Alarm goes off |
|---|---|
| `5` | in 5 seconds (good for a quick test) |
| `45s`, `10m`, `1h30m` | after that long |
| `7:30`, `07:30`, `7:30pm`, `6pm` | at that time of day (tomorrow if it has already passed today) |

With no time given, the alarm goes off after 5 seconds.

- Before the alarm rings, press **Ctrl+C** in the terminal to cancel it.
- While it's ringing, **Esc** closes the camera window.

## Turning the alarm off
When the alarm rings, the app randomly picks one challenge:

| Challenge | What to do |
|---|---|
| Double bicep | Flex both arms with your fists above your shoulders and hold for 5 seconds (a reference picture is shown in the corner) |
| Hands above head | Raise both hands above your head and hold for 5 seconds |
| Squat | Bend both knees into a squat and hold for 5 seconds |
| Toe touch | Bend over and reach both hands down past your knees toward your toes, keeping your legs mostly straight, and hold for 5 seconds |
| Jumping jacks | Do 5 jumping jacks, bringing your arms all the way up and back down each time |
| Pushups | Do 5 pushups, side-on to the camera, going down until your elbows bend past 100 degrees and back up |

Holding a pose for 5 seconds means holding it the whole time; dropping out of it restarts the timer. Stand far enough back that the camera can see your upper body, or your whole body for squats and toe touches, in a well-lit room. For pushups, put the camera on the floor so it sees you from the side.

## Running the evaluation
Two options make testing easier:
- `--challenge NAME` always uses that challenge instead of a random one: `double_bi`, `hands_up`, `squat`, `toe_touch`, `jumping_jacks`, or `pushups`
- `--log FILE.csv --participant NAME` adds a row to a CSV after each alarm (challenge, completed/quit, seconds to finish, reps counted, how often a person was detected)

**Accuracy test.** For each person and each challenge, run:
```
python src/alarm_app.py 3 --challenge jumping_jacks --log results.csv --participant p1
```
For jumping jacks, someone watching counts how many jumping jacks the person really did before the app reached 5, and types that number into the `actual_reps` column of `results.csv`.

**False trigger test.** Log these to a separate file. Start a pose challenge, have the person move around normally in front of the camera for 30 seconds without doing the pose (walking, sitting, stretching), then press Esc:
```
python src/alarm_app.py 3 --challenge double_bi --log false_triggers.csv --participant p1
```
Any run marked `completed` turned the alarm off by mistake.

**Results table.** Summarize either file with:
```
python src/summarize_log.py results.csv
```

## Project layout
```
src/
  alarm_app.py   main program: alarm time, sound, camera loop
  poses.py       pose challenges (double bicep, hands above head, squat, toe touch)
  actions.py     rep-counted challenges (jumping jacks, pushups)
  landmarks.py   MediaPipe body point numbers
  utils.py       shared helpers (angles, drawing on the video)
  summarize_log.py  turns a --log CSV into a results table
models/          MediaPipe pose landmarker model
```

To add a new pose or action, see the instructions at the top of `src/poses.py` or `src/actions.py`.

The `.py` files in the top folder (`alarm_app.py`, `alarm_test.py`, `cam_plus_skeleton.py`, `cv_hello_world.py`, `media_pipe_test.py`) are early prototypes kept for reference. The app is `src/alarm_app.py`.
