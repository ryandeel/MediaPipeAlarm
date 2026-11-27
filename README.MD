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

## Window version (GUI)
If you'd rather set the alarm on screen than type it in the terminal, run:
```
python src/alarm_gui.py
```

A full-screen window opens with a clock and a box for the alarm time.

1. Type a time in the box (same formats as the table above: `7:30am`, `6pm`, `10m`, `45s`...) and press **Set alarm** or **Enter**. You can also click one of the quick buttons: `10s`, `1m`, `5m`, `30m`, `7:00am`.
2. The window counts down to the alarm. Press **Cancel** to clear it.
3. Leave the window open. When the time comes, the alarm sounds and the camera video appears in the same window under a flashing **WAKE UP!** banner.
4. Do the challenge shown on screen. Once it's done, the window goes back to the start screen and says **Alarm off. Good morning!**, ready for the next alarm.

When the alarm goes off, a loading screen shows while the pose model loads and the camera starts (a few seconds), then the video appears.

While the alarm is ringing, **Esc** stops it and takes you back to the start screen (marked **Alarm stopped** rather than completed), and the window's **X** button stops it and closes the window.

The alarm only goes off while the window is open and the computer is awake. Closing the window before it rings cancels the alarm.

### Keyboard
| Key | What it does |
|---|---|
| **F11** | Full screen on/off (the window starts in full screen) |
| **Esc** | Stop a ringing alarm; otherwise leave full screen |
| **Ctrl +** / **Ctrl −** | Bigger / smaller text, **Ctrl 0** resets it |
| **Tab** / **Shift+Tab** | Move between the time box and buttons |
| **Enter** or **Space** | Press the highlighted button |

### Picking a challenge and logging from the window
Every option from [Running the evaluation](#running-the-evaluation) works with the window too. Add it when you start the window and it applies to every alarm you set from it:

```
python src/alarm_gui.py --challenge pushups
python src/alarm_gui.py --log results.csv --participant p1
python src/alarm_gui.py --challenge toe_touch --log results.csv --participant p1
```

- `--challenge NAME` makes every alarm use that challenge instead of a random one: `double_bi`, `hands_up`, `squat`, `toe_touch`, `jumping_jacks`, or `pushups`.
- `--log FILE.csv --participant NAME` adds one row to the CSV each time an alarm goes off, the same as `alarm_app.py`. The file is saved in the folder you ran the command from.
- `--debug` shows the debug info (angles etc.) on the video.

The time is always set in the window, so don't put a time on the command line. If an option is mistyped, the window shows **Error: bad command-line flag, see the terminal** when the alarm goes off, and the terminal says what was wrong.

For testing several people in a row, keep the window open and set a short alarm (for example `10s`) for each run, changing `--participant` by restarting the window between people.

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
  alarm_gui.py   window version: set the alarm on screen, runs alarm_app.py inside the window
  poses.py       pose challenges (double bicep, hands above head, squat, toe touch)
  actions.py     rep-counted challenges (jumping jacks, pushups)
  landmarks.py   MediaPipe body point numbers
  utils.py       shared helpers (angles, drawing on the video)
  summarize_log.py  turns a --log CSV into a results table
models/          MediaPipe pose landmarker model
```

To add a new pose or action, see the instructions at the top of `src/poses.py` or `src/actions.py`.

The `.py` files in the top folder (`alarm_app.py`, `alarm_test.py`, `cam_plus_skeleton.py`, `cv_hello_world.py`, `media_pipe_test.py`) are early prototypes kept for reference. The app is `src/alarm_app.py`.
